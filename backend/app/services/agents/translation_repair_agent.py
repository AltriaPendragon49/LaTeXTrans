"""
translation_repair_agent.py
eliminate-silent-fallback — Phase 3 Specialized Repair Agent
reduce-translation-fallbacks — Context-Aware Repair Enhancements

TranslationRepairAgent: Performs bounded, minimal LLM-backed repair on
fallback segments identified by FallbackReport. Operates under strict
constraints:
  - Preserves all placeholders (PLACEHOLDER_ENV_*, PLACEHOLDER_CAP_*, etc.)
  - Preserves all protected tokens (LaTeX commands, math delimiters)
  - Must NOT introduce new macros or environments
  - Respects a per-edit token budget (MAX_EDIT_TOKENS)
  - Does NOT use external search tools or general knowledge retrieval

All authority (LLM calls) is strictly bounded by:
  - MAX_REPAIR_RETRIES in the orchestrator (global cycle limit)
  - Per-call placeholder guard (output validated before acceptance)
"""
from __future__ import annotations

import asyncio
import logging
import math
import re
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
from .llm_runtime import build_llm_client_timeout, resolve_llm_timeout
from .llm_token_pool import post_chat_completion_with_pool

from .pipeline_schema import FallbackReport

logger = logging.getLogger(__name__)

# Maximum token delta allowed between original and repaired text.
# Prevents the repair agent from hallucinating large new sections.
MAX_EDIT_TOKENS = 512

# Maximum source token count for Total Erasure recovery.
# If source exceeds this threshold, LLM recovery is skipped and the segment
# is immediately downgraded to Phase 3 (ultimate downgrade).
MAX_ERASURE_RECOVERY_TOKENS = 256

# Regex patterns for placeholder detection (read-only guard)
_PLACEHOLDER_PATTERN = re.compile(
    r"<PLACEHOLDER_(?:ENV|CAP|ITEM|EQROW|MATH)_\d+>"
)

# Complex math environments that MUST NOT be repaired by the math guard.
# This blacklist is intentionally conservative: it covers only the most
# well-known multi-line environments.  Do NOT expand it without a dedicated
# spec change — adding environments here suppresses the math delimiter guard
# for entire blocks, which could mask real mismatches.
_COMPLEX_MATH_ENVS = re.compile(
    r"\\begin\{(align\*?|cases|eqnarray\*?|gather\*?|multline\*?)\}"
)


def _extract_placeholders(text: str) -> set[str]:
    """Extract all placeholder tokens from text for guard validation."""
    return set(_PLACEHOLDER_PATTERN.findall(text or ""))


def _estimate_tokens(text: str) -> int:
    """Rough token estimate (UTF-8 bytes / 3, matching token_estimator_v1)."""
    if not text:
        return 0
    return int(math.ceil(len(text.encode("utf-8")) / 3.0))


def _count_math_delimiters(text: str) -> int:
    """Count explicit math delimiters in *text*: bare ``$``, ``\\(``, ``\\)``.

    ``$$`` display-math pairs are NOT counted here — they are a structurally
    different delimiter class and handled by the compiler.  This function
    intentionally does not attempt to validate math semantics; it only counts
    delimiter tokens to let the guard detect mismatches introduced during
    LLM repair.

    Args:
        text: LaTeX source or translated text.

    Returns:
        Total count of ``$`` (excluding ``$$``), ``\\(``, and ``\\)`` tokens.
    """
    if not text:
        return 0
    # Count \( and \)
    paren_count = len(re.findall(r"\\\(|\\\)", text))
    # Count lone $ (not part of $$). Strategy: remove $$ pairs first, then count $
    stripped = re.sub(r"\$\$", "", text)
    dollar_count = stripped.count("$")
    return dollar_count + paren_count


def _math_delimiter_guard(source: str, repaired: str) -> bool:
    """Return True if *repaired* has the same math delimiter count as *source*.

    Skips the check entirely when the source contains a complex math
    environment (align, cases, …) — those blocks are allowed to have
    unbalanced inline delimiters by design and MUST NOT be repaired.

    Returns:
        True  → delimiter counts match (or check skipped for complex envs).
        False → mismatch detected; caller must reject the repair.
    """
    if _COMPLEX_MATH_ENVS.search(source or ""):
        return True  # complex env — skip delimiter check
    src_count = _count_math_delimiters(source)
    rep_count = _count_math_delimiters(repaired)
    return src_count == rep_count


def _placeholder_guard(original: str, repaired: str) -> bool:
    """Return True if repaired text preserves all placeholders from original.

    Spec constraint: TranslationRepairAgent MUST preserve all placeholder tokens.
    """
    return _extract_placeholders(original) == _extract_placeholders(repaired)


def _edit_budget_check(original: str, repaired: str) -> bool:
    """Return True if the token delta is within MAX_EDIT_TOKENS.

    Prevents the repair agent from producing massive new text.
    """
    delta = abs(_estimate_tokens(repaired) - _estimate_tokens(original))
    return delta <= MAX_EDIT_TOKENS


def _no_new_macro_guard(original: str, repaired: str) -> bool:
    """Return True if repaired text doesn't introduce new LaTeX macros.

    Spec constraint: Must not introduce new macros or environments.
    Checks that any \\begin{X} block in repaired also exists in original.
    """
    orig_envs = set(re.findall(r"\\begin\{(\w+\*?)\}", original or ""))
    new_envs = set(re.findall(r"\\begin\{(\w+\*?)\}", repaired or ""))
    introduced = new_envs - orig_envs
    if introduced:
        logger.warning("Repair rejected: new environments introduced: %s", introduced)
        return False
    return True


class TranslationRepairAgent:
    """Bounded LLM repair agent for fallback segments.

    Invoked by node_repair_translation in the orchestrator. Does NOT
    participate in the main translation loop.
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
        llm_cfg = config.get("llm_config") or {}
        self.model = llm_cfg.get("model", "gpt-4o")
        self.base_url = llm_cfg.get("base_url")
        self.api_key = llm_cfg.get("api_key")
        self.timeout_seconds = resolve_llm_timeout(config, default=120)
        self.target_language = config.get("target_language", "zh")
        self.source_language = config.get("source_language", "en")
        self._reserve_remedial_llm_call = config.get("_reserve_remedial_llm_call")

    def _uses_system_pool(self) -> bool:
        return str(self.config.get("llm_config", {}).get("pool_mode") or "").strip() == "system_managed"

    @staticmethod
    def _infer_part_type(chunk_scope: str) -> str:
        scope = str(chunk_scope or "")
        if scope.startswith("<PLACEHOLDER_ENV_"):
            return "env"
        if scope.startswith("<PLACEHOLDER_CAP_"):
            return "cap"
        return "sec"

    @staticmethod
    def _normalized_failure_signature(report: FallbackReport) -> str:
        evidence = report.validation_evidence or {}
        evidence_bits = []
        if isinstance(evidence, dict):
            for key in sorted(evidence):
                evidence_bits.append(f"{key}={evidence.get(key)}")
        root_cause = report.root_cause or ""
        return f"{report.chunk_scope}|{report.fallback_kind}|{root_cause}|{'|'.join(evidence_bits)}"

    @staticmethod
    def _should_skip_non_translatable(report: FallbackReport, target_dict: Dict[str, Any]) -> bool:
        if not isinstance(target_dict, dict):
            return False
        if target_dict.get("immutable_only"):
            return True
        if target_dict.get("chunk_kind") == "placeholder_only":
            return True
        if target_dict.get("translation_status") == "immutable_passthrough":
            return True
        if target_dict.get("fallback_reason") == "oversize_no_safe_boundary":
            return True
        evidence = report.validation_evidence or {}
        math_error = ""
        ph_error = ""
        if isinstance(evidence, dict):
            math_error = str(evidence.get("math_error") or "")
            ph_error = str(evidence.get("ph_error") or "")
        if "env_restore_failed" in math_error:
            return True
        if "Missing placeholders:" in ph_error and int(target_dict.get("translatable_char_count") or 0) == 0:
            return True
        return False

    # ------------------------------------------------------------------
    # Prompt construction — three context-aware branches
    # ------------------------------------------------------------------

    def _build_repair_prompt(self, report: FallbackReport, original_text: str) -> str:
        """Build a focused, context-aware repair prompt from FallbackReport.

        Three branches (resolved in order):

        1. **Total Erasure** — ``translated_text`` is empty AND source is within
           the token gate.  Instructs the LLM to perform a structural recovery
           translation while preserving all LaTeX structure.

        2. **Math Mismatch** — ``validation_evidence`` signals a
           ``math_delimiter_mismatch``.  Instructs the LLM to balance explicit
           math delimiters based on literal source counts; forbids complex-env
           repair.

        3. **General** — Any other failure.  Minimal structural fix with full
           placeholder / anchor preservation instructions.
        """
        lang = self.target_language
        src_lang = self.source_language
        evidence = report.validation_evidence or {}
        translated = report.translated_text or ""

        # ---- Branch 1: Total Erasure recovery --------------------------------
        if not translated:
            return (
                f"You are a LaTeX translation recovery assistant.\n"
                f"The following {src_lang} text was sent for translation but the model "
                f"returned an empty response (Total Erasure).\n"
                f"Your task: perform a structural recovery translation into {lang}.\n"
                f"\n"
                f"STRICT RULES (MANDATORY):\n"
                f"  1. Translate the natural-language content into {lang}.\n"
                f"  2. Preserve ALL LaTeX commands, math delimiters, and placeholders exactly as-is.\n"
                f"  3. Do NOT introduce any new LaTeX environments or macros.\n"
                f"  4. Preserve ALL placeholder tokens exactly "
                f"(e.g., <PLACEHOLDER_ENV_1>, <PLACEHOLDER_CAP_2>).\n"
                f"  5. Output ONLY the translated LaTeX text, nothing else.\n"
                f"\nSource text to translate:\n{original_text}"
            )

        # ---- Branch 2: Math delimiter mismatch -------------------------------
        root_cause = evidence.get("math_error", "") or report.root_cause or ""
        if "math_delimiter_mismatch" in root_cause:
            src_dollar = _count_math_delimiters(original_text)
            return (
                f"You are a LaTeX math-delimiter repair assistant.\n"
                f"The translated text below has a math-delimiter mismatch.\n"
                f"The source text contains exactly {src_dollar} explicit math delimiter(s) "
                f"(counting bare `$` and `\\(` / `\\)` pairs — NOT `$$`).\n"
                f"\n"
                f"STRICT RULES (MANDATORY):\n"
                f"  1. Adjust ONLY the math delimiters (`$`, `\\(`, `\\)`) in the translated "
                f"text so the final count matches {src_dollar}.\n"
                f"  2. Do NOT repair or touch any complex math environment "
                f"(align, cases, eqnarray, gather, multline).\n"
                f"  3. Do NOT translate, rephrase, or alter any text content.\n"
                f"  4. Preserve ALL placeholder tokens exactly as-is.\n"
                f"  5. Output ONLY the repaired LaTeX text, nothing else.\n"
                f"\nTranslated text requiring math-delimiter repair:\n{translated}"
            )

        # ---- Branch 3: General structural repair -----------------------------
        error_detail = evidence.get("math_error", "") or report.root_cause or "unknown"
        return (
            f"You are a LaTeX translation repair assistant.\n"
            f"The following {src_lang} text was translated to {lang} but the output "
            f"failed validation due to: {error_detail} (kind: {report.fallback_kind}).\n"
            f"Rules (MANDATORY):\n"
            f"  1. Do NOT add new LaTeX environments or macros.\n"
            f"  2. Preserve ALL placeholder tokens exactly as-is "
            f"(e.g., <PLACEHOLDER_ENV_1>, <PLACEHOLDER_CAP_2>).\n"
            f"  3. Preserve ALL list-item anchors (e.g., <ITEM_1>, <ITEM_2>) exactly as-is.\n"
            f"  4. Fix only LaTeX structural issues — do not rephrase the translation.\n"
            f"  5. Output only the repaired LaTeX text, nothing else.\n"
            f"\nText to repair:\n{translated or original_text}"
        )

    async def _call_llm_repair(
        self,
        prompt: str,
        original_text: str,
        *,
        chunk_scope: str,
    ) -> Optional[str]:
        """Call LLM for repair. Returns repaired text or None on failure."""
        if not self.base_url or not self.api_key:
            logger.warning("TranslationRepairAgent: no API config, skipping LLM repair")
            return None
        reserve = self._reserve_remedial_llm_call
        if callable(reserve) and not reserve(
            "repair_translation",
            part_type=self._infer_part_type(chunk_scope),
            identifier=str(chunk_scope),
        ):
            logger.warning(
                "TranslationRepairAgent: skipping repair for %s because remedial budget is exhausted",
                chunk_scope,
            )
            return None

        try:
            import aiohttp

            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": original_text},
                ],
                "temperature": 0.3,
                "max_new_tokens": 4096,
            }
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            timeout = build_llm_client_timeout(self.config, default=self.timeout_seconds)
            async with aiohttp.ClientSession() as session:
                if self._uses_system_pool():
                    result = await post_chat_completion_with_pool(
                        session=session,
                        llm_config=self.config.get("llm_config", {}),
                        payload=payload,
                        timeout=timeout,
                    )
                    return result["choices"][0]["message"]["content"].strip()
                async with session.post(
                    self.base_url, json=payload, headers=headers, timeout=timeout
                ) as resp:
                    if resp.status != 200:
                        logger.warning("Repair LLM returned HTTP %s", resp.status)
                        return None
                    result = await resp.json()
                    return result["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            logger.warning("TranslationRepairAgent LLM call failed: %s", exc)
            return None

    async def _repair_one(
        self,
        report: FallbackReport,
        original_text: str,
    ) -> Optional[str]:
        """Attempt LLM repair for a single segment. Returns repaired text or None.

        Pre-LLM gate:
          - Token gate: if Total Erasure AND source exceeds MAX_ERASURE_RECOVERY_TOKENS,
            skip LLM entirely and return None (direct downgrade).

        Post-LLM gates (any failure → return None, no retry):
          - Gate 1: placeholder guard
          - Gate 2: no new macro guard
          - Gate 3: edit budget
          - Gate 4: math delimiter guard

        Returns None on any gate failure. Caller is responsible for
        triggering ultimate downgrade.
        """
        # ---- Pre-LLM token gate (Total Erasure path) ------------------------
        translated = report.translated_text or ""
        if not translated and report.fallback_kind != "oversize_downgrade":
            source_tokens = _estimate_tokens(original_text)
            if source_tokens > MAX_ERASURE_RECOVERY_TOKENS:
                logger.warning(
                    "TranslationRepairAgent [token-gate]: chunk %s has %d source tokens "
                    "> MAX_ERASURE_RECOVERY_TOKENS=%d — skipping LLM, triggering downgrade",
                    report.chunk_scope,
                    source_tokens,
                    MAX_ERASURE_RECOVERY_TOKENS,
                )
                return None, "token-gate"

        prompt = self._build_repair_prompt(report, original_text)
        repaired = await self._call_llm_repair(
            prompt,
            original_text,
            chunk_scope=str(report.chunk_scope),
        )
        if repaired is None:
            return None, "llm-failure"

        # Gate 1: placeholder guard
        if not _placeholder_guard(original_text, repaired):
            logger.warning(
                "TranslationRepairAgent [placeholder-guard]: chunk %s — "
                "placeholder mismatch, rejecting repair and triggering downgrade",
                report.chunk_scope,
            )
            return None, "placeholder-guard"

        # Gate 2: no new macro guard
        if not _no_new_macro_guard(original_text, repaired):
            logger.warning(
                "TranslationRepairAgent [macro-guard]: chunk %s — "
                "new macro/env introduced, rejecting repair and triggering downgrade",
                report.chunk_scope,
            )
            return None, "macro-guard"

        # Gate 3: edit budget
        if not _edit_budget_check(original_text, repaired):
            logger.warning(
                "TranslationRepairAgent [budget-guard]: chunk %s — "
                "edit budget exceeded, rejecting repair and triggering downgrade",
                report.chunk_scope,
            )
            return None, "budget-guard"

        # Gate 4: math delimiter guard
        if not _math_delimiter_guard(original_text, repaired):
            logger.warning(
                "TranslationRepairAgent [math-guard]: chunk %s — "
                "math delimiter count mismatch after repair, rejecting and triggering downgrade",
                report.chunk_scope,
            )
            return None, "math-guard"

        return repaired, None

    async def repair(
        self,
        fallback_reports: List[FallbackReport],
        sections: List[Dict[str, Any]],
        envs: List[Dict[str, Any]],
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Apply bounded LLM repair to all fallback segments.

        Modifies sections and envs in-place (copies returned).
        Skips repair for oversize_downgrade (LLM would face the same length issue).
        """
        sections = list(sections)
        envs = list(envs)
        repair_events: List[Dict[str, Any]] = []
        seen_signatures: set[str] = set()

        for report in fallback_reports:
            matched_sec = next(
                (s for s in sections if str(s.get("section", "")) == report.chunk_scope),
                None,
            )
            matched_env = next(
                (e for e in envs if str(e.get("placeholder", "")) == report.chunk_scope),
                None,
            )
            
            target_dict = matched_sec if matched_sec is not None else matched_env
            if target_dict is None:
                continue

            failure_signature = self._normalized_failure_signature(report)
            if failure_signature in seen_signatures:
                target_dict["repair_rejection_reason"] = "deduplicated-same-failure"
                repair_events.append({
                    "event": "repair_deduplicated_same_failure",
                    "chunk_scope": report.chunk_scope,
                    "fallback_kind": report.fallback_kind,
                })
                continue
            seen_signatures.add(failure_signature)

            if self._should_skip_non_translatable(report, target_dict):
                target_dict["translation_status"] = "repair_skipped_non_translatable"
                target_dict["repair_rejection_reason"] = "non-translatable-chunk"
                repair_events.append({
                    "event": "repair_skipped_immutable_chunk",
                    "chunk_scope": report.chunk_scope,
                    "fallback_kind": report.fallback_kind,
                })
                continue

            original = target_dict.get("trans_content") or target_dict.get("content") or ""

            # oversize segments cannot be repaired by LLM (same token limit applies)
            if report.fallback_kind == "oversize_downgrade":
                logger.info(
                    "TranslationRepairAgent: skipping oversize segment %s (LLM limit applies)",
                    report.chunk_scope,
                )
                target_dict["repair_rejection_reason"] = "oversize-downgrade"
                continue
                
            # C2 structural collapse must be downgraded immediately without LLM repair
            if report.fallback_kind == "c2_structural_collapse":
                logger.info(
                    "TranslationRepairAgent: skipping c2_structural_collapse segment %s (direct downgrade)",
                    report.chunk_scope,
                )
                target_dict["repair_rejection_reason"] = "c2-direct-downgrade"
                continue

            repaired, rejection_reason = await self._repair_one(report, original)
            if repaired is not None:
                target_dict["trans_content"] = repaired
                target_dict["translation_status"] = "repair_applied"
                logger.info(
                    "TranslationRepairAgent: repaired segment/env %s", report.chunk_scope
                )
            elif rejection_reason:
                target_dict["repair_rejection_reason"] = rejection_reason

        return sections, envs, repair_events

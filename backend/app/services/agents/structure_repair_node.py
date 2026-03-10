"""
structure_repair_node.py
eliminate-silent-fallback — Phase 3 Deterministic Structure Repair

StructureRepairNode: Applies deterministic, non-LLM bracket and environment
mismatch fixes to fallback segments.

Design constraints (from spec):
  - MUST use deterministic, non-LLM logic only.
  - If repair safety cannot be guaranteed, the repair is rejected.
  - Handles unclosed braces { and \\begin{}/\\end{} mismatches.
  - Returns the repaired segments with repair_rejected=True metadata
    if safety constraints fail.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from .pipeline_schema import FallbackReport

logger = logging.getLogger(__name__)


def _count_open_braces(text: str) -> int:
    """Count net open braces (unclosed `{`) in text, skipping escaped ones."""
    depth = 0
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "\\" and i + 1 < len(text):
            i += 2  # skip escaped character
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        i += 1
    return depth


def _repair_unclosed_braces(text: str) -> Tuple[Optional[str], bool]:
    """Close unmatched `{` at the end of text if the count is unambiguous.

    Returns (repaired_text, success). If depth < 0 (extra `}`), rejects repair.
    """
    depth = _count_open_braces(text)
    if depth == 0:
        return text, True
    if depth < 0:
        # More closing braces than opening — ambiguous, reject
        return None, False
    # Append the missing closing braces
    repaired = text + ("}" * depth)
    return repaired, True


def _find_unmatched_environments(text: str) -> List[str]:
    """Return list of environment names that are opened but not closed."""
    opens = re.findall(r"\\begin\{(\w+\*?)\}", text or "")
    closes = re.findall(r"\\end\{(\w+\*?)\}", text or "")

    # Use a stack-based approach
    from collections import Counter
    open_counts = Counter(opens)
    close_counts = Counter(closes)
    unmatched = []
    for env, cnt in open_counts.items():
        missing = cnt - close_counts.get(env, 0)
        if missing > 0:
            unmatched.extend([env] * missing)
    return unmatched


def _repair_unmatched_environments(text: str) -> Tuple[Optional[str], bool]:
    """Close unmatched \\begin{X} environments if safe.

    Safety check: only repairs if ≤ 3 environments are unmatched (bounded scope).
    Appends \\end{X} in reverse order of opening.
    """
    opens = re.findall(r"\\begin\{(\w+\*?)\}", text or "")
    closes_set = []
    pos = 0
    for m in re.finditer(r"\\end\{(\w+\*?)\}", text or ""):
        closes_set.append(m.group(1))

    # Stack-based matching
    stack: List[str] = []
    for env in opens:
        stack.append(env)
    for env in closes_set:
        if stack and stack[-1] == env:
            stack.pop()
        else:
            # Mismatched close — ambiguous structure, reject
            logger.debug("StructureRepairNode: ambiguous env mismatch, rejecting")
            return None, False

    if not stack:
        return text, True

    if len(stack) > 3:
        # Too many unclosed environments, reject to prevent garbage output
        logger.warning(
            "StructureRepairNode: %d unclosed environments, too ambiguous — rejecting", len(stack)
        )
        return None, False

    # Append closes in reverse stack order
    suffix = "".join(f"\\end{{{env}}}" for env in reversed(stack))
    return text + "\n" + suffix, True


def _apply_structural_repairs(text: str) -> Tuple[str, bool, str]:
    """Apply all deterministic structural repairs in order.

    Returns (repaired_text, success, description).
    """
    descriptions = []

    # Step 1: Repair unclosed braces
    repaired, ok = _repair_unclosed_braces(text)
    if not ok:
        return text, False, "brace_repair_rejected"
    if repaired != text:
        descriptions.append("braces_closed")
        text = repaired

    # Step 2: Repair unmatched environments
    repaired, ok = _repair_unmatched_environments(text)
    if not ok:
        return text, False, "env_repair_rejected"
    if repaired != text:
        descriptions.append("envs_closed")
        text = repaired

    desc = ",".join(descriptions) if descriptions else "no_change"
    return text, True, desc


class StructureRepairNode:
    """Deterministic bracket/environment repair node (no LLM).

    Spec constraint: MUST use deterministic logic only. If safety cannot
    be guaranteed, repair is rejected and original text is kept.
    """

    def repair(
        self,
        fallback_reports: List[FallbackReport],
        sections: List[Dict[str, Any]],
        envs: List[Dict[str, Any]],
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Apply structural repair to fallback segments.

        Modifies sections and envs in-place (copies returned).
        Only processes c2_structural_collapse and c1_structural_rollback;
        oversize_downgrade segments are skipped (no structure to fix).
        """
        sections = list(sections)
        envs = list(envs)

        for report in fallback_reports:
            if report.fallback_kind == "oversize_downgrade":
                continue

            # Try sections
            matched_sec = next(
                (s for s in sections if str(s.get("section", "")) == report.chunk_scope),
                None,
            )
            if matched_sec is not None:
                text = matched_sec.get("trans_content") or matched_sec.get("content") or ""
                if text:
                    repaired, ok, desc = _apply_structural_repairs(text)
                    if ok and repaired != text:
                        matched_sec["trans_content"] = repaired
                        matched_sec["structure_repair_applied"] = desc
                        logger.info(
                            "StructureRepairNode: repaired section %s (%s)",
                            report.chunk_scope, desc,
                        )
                    elif not ok:
                        matched_sec["structure_repair_rejected"] = True
                        logger.info(
                            "StructureRepairNode: rejected repair for section %s (%s)",
                            report.chunk_scope, desc,
                        )
                continue

            # Try envs
            matched_env = next(
                (e for e in envs if str(e.get("placeholder", "")) == report.chunk_scope),
                None,
            )
            if matched_env is not None:
                text = matched_env.get("trans_content") or matched_env.get("content") or ""
                if text:
                    repaired, ok, desc = _apply_structural_repairs(text)
                    if ok and repaired != text:
                        matched_env["trans_content"] = repaired
                        matched_env["structure_repair_applied"] = desc
                        logger.info(
                            "StructureRepairNode: repaired env %s (%s)",
                            report.chunk_scope, desc,
                        )
                    elif not ok:
                        matched_env["structure_repair_rejected"] = True
                        logger.info(
                            "StructureRepairNode: rejected repair for env %s (%s)",
                            report.chunk_scope, desc,
                        )

        return sections, envs

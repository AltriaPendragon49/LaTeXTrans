"""
Deterministic LaTeX structure guard used before compilation.

The guard is intentionally lightweight and conservative:
- It checks braces/env stack on non-comment, non-verbatim-like text.
- It detects malformed \\resizebox macro arguments.
- It runs LatexWalker on full assembled project text and only hard-fails
  for explicit structural parse signatures.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import logging
import re
import time

from pylatexenc.latexwalker import LatexWalker


logger = logging.getLogger(__name__)


VERBATIM_LIKE_ENVS: Set[str] = {"verbatim", "lstlisting", "minted"}

REASON_UNBALANCED_BRACES = "structure_unbalanced_braces"
REASON_ENV_STACK_MISMATCH = "structure_env_stack_mismatch"
REASON_RESIZEBOX_UNCLOSED = "structure_resizebox_unclosed"
REASON_WALKER_UNEXPECTED_CLOSING = "structure_latexwalker_unexpected_closing_env"
REASON_WALKER_EOF_MACRO_ARGS = "structure_latexwalker_eof_macro_args"
REASON_PLACEHOLDER_RESIDUAL = "structure_placeholder_residual"
REASON_ENV_PLACEHOLDER_RESIDUAL = "structure_env_placeholder_residual"
REASON_MISSING_END_DOCUMENT = "structure_missing_end_document"

_PLACEHOLDER_RESIDUAL_RE = re.compile(r"<PLACEHOLDER_[^>]+>")
_ENV_PLACEHOLDER_RESIDUAL_RE = re.compile(r"<ENV(?:_BEGIN|_END)?_[^>]+>")
_END_DOCUMENT_RE = re.compile(r"\\end\s*\{document\}")
_BEGIN_DOCUMENT_RE = re.compile(r"\\begin\s*\{document\}")
_SIMPLE_MACRO_BODY_RE = re.compile(
    r"\\(?:preauthor|postauthor|predate|postdate|pretitle|posttitle|author|title|thanks)\b"
)
_NEWCOMMAND_RE = re.compile(
    r"\\(?:newcommand|renewcommand|providecommand|DeclareRobustCommand|newenvironment|renewenvironment)\*?"
)
_DEF_COMMAND_RE = re.compile(r"\\(?:gdef|edef|xdef|def)\b")


@dataclass
class StructureGuardResult:
    ok: bool
    reason_code: Optional[str] = None
    message: str = ""
    details: Optional[Dict[str, Any]] = None
    warning_only: bool = False
    guard_blocking: Optional[bool] = None
    guard_scope: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        guard_blocking = self.guard_blocking
        if guard_blocking is None:
            guard_blocking = (not self.ok) and (not self.warning_only)
        return {
            "ok": self.ok,
            "reason_code": self.reason_code,
            "message": self.message,
            "details": self.details or {},
            "warning_only": self.warning_only,
            "guard_blocking": guard_blocking,
            "guard_scope": self.guard_scope or "project",
        }


def _is_escaped(text: str, idx: int) -> bool:
    slash_count = 0
    j = idx - 1
    while j >= 0 and text[j] == "\\":
        slash_count += 1
        j -= 1
    return (slash_count % 2) == 1


def _strip_line_comments(text: str) -> str:
    lines: List[str] = []
    for line in text.splitlines():
        cut = None
        for i, ch in enumerate(line):
            if ch == "%" and not _is_escaped(line, i):
                cut = i
                break
        lines.append(line if cut is None else line[:cut])
    return "\n".join(lines)


def _mask_verbatim_like_envs(text: str) -> str:
    masked = text
    for env in VERBATIM_LIKE_ENVS:
        # Keep length stable for easier debugging offsets.
        pattern = re.compile(
            rf"\\begin\{{{re.escape(env)}\}}.*?\\end\{{{re.escape(env)}\}}",
            re.DOTALL,
        )
        masked = pattern.sub(lambda m: " " * len(m.group(0)), masked)
    return masked


def _consume_braced_group(text: str, start: int) -> int:
    if start >= len(text) or text[start] != "{":
        return -1
    depth = 0
    i = start
    while i < len(text):
        ch = text[i]
        if ch == "{" and not _is_escaped(text, i):
            depth += 1
        elif ch == "}" and not _is_escaped(text, i):
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return -1


def _consume_optional_bracket_group(text: str, start: int) -> int:
    if start >= len(text) or text[start] != "[":
        return -1
    depth = 0
    i = start
    while i < len(text):
        ch = text[i]
        if ch == "[" and not _is_escaped(text, i):
            depth += 1
        elif ch == "]" and not _is_escaped(text, i):
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return -1


def _consume_command_token(text: str, start: int) -> int:
    if start >= len(text) or text[start] != "\\":
        return -1
    i = start + 1
    if i >= len(text):
        return i
    if text[i].isalpha() or text[i] == "@":
        while i < len(text) and (text[i].isalpha() or text[i] == "@"):
            i += 1
        return i
    return i + 1


def _skip_ws(text: str, start: int) -> int:
    i = start
    while i < len(text) and text[i].isspace():
        i += 1
    return i


def _coalesce_spans(spans: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    if not spans:
        return []
    spans = sorted(spans)
    merged: List[Tuple[int, int]] = [spans[0]]
    for start, end in spans[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged


def _mask_spans(text: str, spans: List[Tuple[int, int]]) -> str:
    if not spans:
        return text
    chars = list(text)
    for start, end in _coalesce_spans(spans):
        for idx in range(max(start, 0), min(end, len(chars))):
            if chars[idx] != "\n":
                chars[idx] = " "
    return "".join(chars)


def _collect_macro_body_spans(text: str) -> List[Tuple[int, int]]:
    spans: List[Tuple[int, int]] = []

    for match in _SIMPLE_MACRO_BODY_RE.finditer(text):
        body_start = _skip_ws(text, match.end())
        body_end = _consume_braced_group(text, body_start)
        if body_end != -1:
            spans.append((body_start, body_end))

    for match in _NEWCOMMAND_RE.finditer(text):
        cursor = _skip_ws(text, match.end())
        if cursor < len(text) and text[cursor] == "{":
            cursor = _consume_braced_group(text, cursor)
        elif cursor < len(text) and text[cursor] == "\\":
            cursor = _consume_command_token(text, cursor)
        else:
            continue
        if cursor == -1:
            continue
        while True:
            next_cursor = _skip_ws(text, cursor)
            bracket_end = _consume_optional_bracket_group(text, next_cursor)
            if bracket_end == -1:
                cursor = next_cursor
                break
            cursor = bracket_end
        body_groups = 2 if "environment" in match.group(0) else 1
        for _ in range(body_groups):
            cursor = _skip_ws(text, cursor)
            body_end = _consume_braced_group(text, cursor)
            if body_end == -1:
                break
            spans.append((cursor, body_end))
            cursor = body_end

    for match in _DEF_COMMAND_RE.finditer(text):
        cursor = _skip_ws(text, match.end())
        if cursor < len(text) and text[cursor] == "\\":
            cursor = _consume_command_token(text, cursor)
        while cursor < len(text) and text[cursor] != "{":
            cursor += 1
        body_end = _consume_braced_group(text, cursor)
        if body_end != -1:
            spans.append((cursor, body_end))

    return _coalesce_spans(spans)


def _mask_macro_argument_bodies(text: str) -> str:
    return _mask_spans(text, _collect_macro_body_spans(text))


def _infer_guard_scope(full_text: str, details: Optional[Dict[str, Any]]) -> str:
    if not details:
        return "project"
    offsets = [
        value for key, value in details.items()
        if key.endswith("offset") and isinstance(value, int)
    ]
    if not offsets:
        nested_warnings = details.get("warnings")
        if isinstance(nested_warnings, list):
            for warning in nested_warnings:
                if not isinstance(warning, dict):
                    continue
                warning_details = warning.get("details")
                if isinstance(warning_details, dict):
                    offsets.extend(
                        value for key, value in warning_details.items()
                        if key.endswith("offset") and isinstance(value, int)
                    )
    if not offsets:
        return "project"
    begin_doc = _BEGIN_DOCUMENT_RE.search(full_text)
    if begin_doc and min(offsets) < begin_doc.start():
        return "preamble"
    return "body"


def _make_warning_result(
    full_text: str,
    *,
    reason_code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
) -> StructureGuardResult:
    scope = _infer_guard_scope(full_text, details)
    return StructureGuardResult(
        ok=True,
        reason_code=reason_code,
        message=message,
        details=details or {},
        warning_only=True,
        guard_blocking=False,
        guard_scope=scope,
    )


def _check_unbalanced_braces(clean_text: str) -> Optional[StructureGuardResult]:
    depth = 0
    for i, ch in enumerate(clean_text):
        if ch == "{" and not _is_escaped(clean_text, i):
            depth += 1
        elif ch == "}" and not _is_escaped(clean_text, i):
            depth -= 1
            if depth < 0:
                return StructureGuardResult(
                    ok=False,
                    reason_code=REASON_UNBALANCED_BRACES,
                    message="Unexpected closing brace detected",
                    details={"offset": i},
                )
    if depth != 0:
        return StructureGuardResult(
            ok=False,
            reason_code=REASON_UNBALANCED_BRACES,
            message="Unbalanced braces detected",
            details={"remaining_open_braces": depth},
        )
    return None


def _check_env_stack(clean_text: str) -> Optional[StructureGuardResult]:
    token_re = re.compile(r"\\(begin|end)\s*\{([^\{\}]+)\}")
    stack: List[Tuple[str, int]] = []
    for m in token_re.finditer(clean_text):
        token = m.group(1)
        env = m.group(2).strip()
        if token == "begin":
            stack.append((env, m.start()))
            continue

        if not stack:
            return StructureGuardResult(
                ok=False,
                reason_code=REASON_ENV_STACK_MISMATCH,
                message=f"Unexpected closing environment: {env}",
                details={"env": env, "offset": m.start()},
            )

        open_env, open_offset = stack.pop()
        if open_env != env:
            return StructureGuardResult(
                ok=False,
                reason_code=REASON_ENV_STACK_MISMATCH,
                message=f"Mismatched environment stack: begin={open_env}, end={env}",
                details={
                    "begin_env": open_env,
                    "end_env": env,
                    "begin_offset": open_offset,
                    "end_offset": m.start(),
                },
            )

    if stack:
        open_env, open_offset = stack[-1]
        return StructureGuardResult(
            ok=False,
            reason_code=REASON_ENV_STACK_MISMATCH,
            message=f"Unclosed environment detected: {open_env}",
            details={"env": open_env, "offset": open_offset},
        )
    return None


def _check_resizebox_closure(clean_text: str) -> Optional[StructureGuardResult]:
    cmd_re = re.compile(r"\\resizebox\b")
    for m in cmd_re.finditer(clean_text):
        i = m.end()
        while i < len(clean_text) and clean_text[i].isspace():
            i += 1
        first_end = _consume_braced_group(clean_text, i)
        if first_end == -1:
            return StructureGuardResult(
                ok=False,
                reason_code=REASON_RESIZEBOX_UNCLOSED,
                message="Malformed resizebox first argument",
                details={"offset": m.start()},
            )
        i = first_end
        while i < len(clean_text) and clean_text[i].isspace():
            i += 1
        second_end = _consume_braced_group(clean_text, i)
        if second_end == -1:
            return StructureGuardResult(
                ok=False,
                reason_code=REASON_RESIZEBOX_UNCLOSED,
                message="Malformed resizebox second argument",
                details={"offset": m.start()},
            )
        i = second_end
        while i < len(clean_text) and clean_text[i].isspace():
            i += 1
        third_end = _consume_braced_group(clean_text, i)
        if third_end == -1:
            return StructureGuardResult(
                ok=False,
                reason_code=REASON_RESIZEBOX_UNCLOSED,
                message="Malformed resizebox body argument",
                details={"offset": m.start()},
            )
    return None


def _check_latexwalker(full_text: str) -> Optional[StructureGuardResult]:
    try:
        LatexWalker(full_text, tolerant_parsing=False).get_latex_nodes()
        return None
    except Exception as exc:
        msg = str(exc)
        msg_lower = msg.lower()
        if "unexpected closing environment" in msg_lower:
            return StructureGuardResult(
                ok=False,
                reason_code=REASON_WALKER_UNEXPECTED_CLOSING,
                message=msg,
            )
        if "end of input while parsing macro arguments" in msg_lower:
            return StructureGuardResult(
                ok=False,
                reason_code=REASON_WALKER_EOF_MACRO_ARGS,
                message=msg,
            )
    return None


def _resolve_input_path(base_dir: Path, raw_ref: str) -> Optional[Path]:
    candidate = raw_ref.strip()
    if not candidate:
        return None
    p = Path(candidate)
    if p.suffix == "":
        p = p.with_suffix(".tex")
    abs_path = (base_dir / p).resolve()
    if abs_path.exists():
        return abs_path
    return None


def _collect_project_text(main_tex_path: Path) -> str:
    active_stack: Set[Path] = set()
    input_re = re.compile(r"\\(?:input|include)\s*\{([^\{\}]+)\}")

    def visit(tex_path: Path) -> str:
        resolved = tex_path.resolve()
        if not resolved.exists():
            return ""
        if resolved in active_stack:
            return ""

        active_stack.add(resolved)
        text = resolved.read_text(encoding="utf-8", errors="replace")
        current_dir = resolved.parent

        def replace_input(match: re.Match[str]) -> str:
            child = _resolve_input_path(current_dir, match.group(1))
            if child is None:
                return match.group(0)
            return visit(child)

        expanded = input_re.sub(replace_input, text)
        active_stack.remove(resolved)
        return expanded

    return visit(main_tex_path)


def validate_project_structure(main_tex_path: str) -> Dict[str, Any]:
    """
    Validate final project LaTeX structure before compilation.

    The input must be the assembled main.tex path inside the compile-ready bundle.
    """
    main_path = Path(main_tex_path)
    started_at = time.perf_counter()

    def _finalize(result: StructureGuardResult) -> Dict[str, Any]:
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        logger.info(
            "Structure guard validated %s: ok=%s reason_code=%s elapsed_ms=%d",
            main_path.name or str(main_path),
            result.ok,
            result.reason_code,
            elapsed_ms,
        )
        return result.as_dict()

    if not main_path.exists():
        return _finalize(StructureGuardResult(
            ok=False,
            reason_code=REASON_ENV_STACK_MISMATCH,
            message=f"Main tex file not found: {main_tex_path}",
            guard_blocking=True,
        ))

    full_text = _collect_project_text(main_path)
    placeholder_residuals = _PLACEHOLDER_RESIDUAL_RE.findall(full_text)
    if placeholder_residuals:
        return _finalize(StructureGuardResult(
            ok=False,
            reason_code=REASON_PLACEHOLDER_RESIDUAL,
            message="Residual PLACEHOLDER tokens detected in assembled project",
            details={"residual": placeholder_residuals[:10]},
            guard_blocking=True,
        ))

    env_placeholder_residuals = _ENV_PLACEHOLDER_RESIDUAL_RE.findall(full_text)
    if env_placeholder_residuals:
        return _finalize(StructureGuardResult(
            ok=False,
            reason_code=REASON_ENV_PLACEHOLDER_RESIDUAL,
            message="Residual synthetic ENV tokens detected in assembled project",
            details={"residual": env_placeholder_residuals[:10]},
            guard_blocking=True,
        ))

    if not _END_DOCUMENT_RE.search(full_text):
        return _finalize(StructureGuardResult(
            ok=False,
            reason_code=REASON_MISSING_END_DOCUMENT,
            message="Missing \\end{document} in assembled project",
            guard_blocking=True,
            guard_scope="body",
        ))

    clean_text = _mask_verbatim_like_envs(_strip_line_comments(full_text))
    masked_clean_text = _mask_verbatim_like_envs(_strip_line_comments(_mask_macro_argument_bodies(full_text)))
    masked_full_text = _mask_macro_argument_bodies(full_text)
    warnings: List[Dict[str, Any]] = []

    for check in (
        _check_unbalanced_braces,
        _check_env_stack,
        _check_resizebox_closure,
    ):
        raw_failure = check(clean_text)
        masked_failure = check(masked_clean_text)
        if masked_failure:
            masked_failure.guard_scope = _infer_guard_scope(full_text, masked_failure.details)
            masked_failure.guard_blocking = True
            return _finalize(masked_failure)
        if raw_failure:
            warnings.append({
                "reason_code": raw_failure.reason_code,
                "message": raw_failure.message,
                "details": raw_failure.details or {},
            })

    raw_walker_failure = _check_latexwalker(full_text)
    masked_walker_failure = _check_latexwalker(masked_full_text)
    if masked_walker_failure:
        masked_walker_failure.guard_scope = _infer_guard_scope(full_text, masked_walker_failure.details)
        masked_walker_failure.guard_blocking = True
        return _finalize(masked_walker_failure)
    if raw_walker_failure:
        warnings.append({
            "reason_code": raw_walker_failure.reason_code,
            "message": raw_walker_failure.message,
            "details": raw_walker_failure.details or {},
        })

    if warnings:
        first_warning = warnings[0]
        return _finalize(_make_warning_result(
            full_text,
            reason_code=str(first_warning.get("reason_code") or REASON_ENV_STACK_MISMATCH),
            message="Structure guard warning only: macro-body structural tokens were ignored",
            details={"warnings": warnings},
        ))

    return _finalize(StructureGuardResult(ok=True, message="structure_guard_passed"))

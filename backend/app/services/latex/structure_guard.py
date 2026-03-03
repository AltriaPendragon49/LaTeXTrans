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
import re

from pylatexenc.latexwalker import LatexWalker


VERBATIM_LIKE_ENVS: Set[str] = {"verbatim", "lstlisting", "minted"}

REASON_UNBALANCED_BRACES = "structure_unbalanced_braces"
REASON_ENV_STACK_MISMATCH = "structure_env_stack_mismatch"
REASON_RESIZEBOX_UNCLOSED = "structure_resizebox_unclosed"
REASON_WALKER_UNEXPECTED_CLOSING = "structure_latexwalker_unexpected_closing_env"
REASON_WALKER_EOF_MACRO_ARGS = "structure_latexwalker_eof_macro_args"


@dataclass
class StructureGuardResult:
    ok: bool
    reason_code: Optional[str] = None
    message: str = ""
    details: Optional[Dict[str, Any]] = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "reason_code": self.reason_code,
            "message": self.message,
            "details": self.details or {},
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


def _resolve_input_path(project_root: Path, raw_ref: str) -> Optional[Path]:
    candidate = raw_ref.strip()
    if not candidate:
        return None
    p = Path(candidate)
    if p.suffix == "":
        p = p.with_suffix(".tex")
    abs_path = (project_root / p).resolve()
    if abs_path.exists():
        return abs_path
    return None


def _collect_project_text(main_tex_path: Path) -> str:
    project_root = main_tex_path.parent
    visited: Set[Path] = set()
    pieces: List[str] = []
    input_re = re.compile(r"\\(?:input|include)\s*\{([^\{\}]+)\}")

    def visit(tex_path: Path) -> None:
        resolved = tex_path.resolve()
        if resolved in visited or not resolved.exists():
            return
        visited.add(resolved)
        text = resolved.read_text(encoding="utf-8", errors="replace")
        pieces.append(text)
        for m in input_re.finditer(text):
            child = _resolve_input_path(project_root, m.group(1))
            if child is not None:
                visit(child)

    visit(main_tex_path)
    return "\n\n".join(pieces)


def validate_project_structure(main_tex_path: str) -> Dict[str, Any]:
    """
    Validate final project LaTeX structure before compilation.

    The input must be the assembled main.tex path inside the compile-ready bundle.
    """
    main_path = Path(main_tex_path)
    if not main_path.exists():
        return StructureGuardResult(
            ok=False,
            reason_code=REASON_ENV_STACK_MISMATCH,
            message=f"Main tex file not found: {main_tex_path}",
        ).as_dict()

    full_text = _collect_project_text(main_path)
    clean_text = _mask_verbatim_like_envs(_strip_line_comments(full_text))

    for check in (
        _check_unbalanced_braces,
        _check_env_stack,
        _check_resizebox_closure,
    ):
        failure = check(clean_text)
        if failure:
            return failure.as_dict()

    walker_failure = _check_latexwalker(full_text)
    if walker_failure:
        return walker_failure.as_dict()

    return StructureGuardResult(ok=True, message="structure_guard_passed").as_dict()


"""
Validator Agent

Adapted from prototype system with:
- All Streamlit dependencies removed
- Progress callback mechanism added
- Python logging integrated
- Validation logic completely preserved
"""

from typing import Dict, Any, List, Optional, Callable
from .base_tool_agent import BaseToolAgent
from .pipeline_invariants import SpeculativeRepairForbiddenError
from pathlib import Path
from collections import Counter
from pylatexenc.latexwalker import LatexWalker
from backend.app.services.latex.utils import (
    anchor_list_items_in_env_body,
    validate_immutable_placeholder_sequence,
)
import os
import re
import logging

logger = logging.getLogger(__name__)

# Error type constants
ERROR_TYPE_A = "A"  # Resource/config missing - handle with degradation
ERROR_TYPE_B = "B"  # Recoverable syntax errors - allow one retry
ERROR_TYPE_C = "C"  # Structural consistency errors - algorithmic fix required (legacy alias)
ERROR_TYPE_C1 = "C1"  # Structural: Local/Contained -- 1 LLM retry allowed
ERROR_TYPE_C2 = "C2"  # Structural: Global/Structural -- NO LLM retry

_LONG_ENGLISH_WORD_RE = re.compile(r"\b[A-Za-z]{2,}(?:'[A-Za-z]{2,})?\b")
_LONG_ENGLISH_GAP_RE = re.compile(r"^[\s,.;:!?()\[\]\"'`~\-–—/\\]+$")
_ALL_CAPS_ACRONYM_RE = re.compile(r"^[A-Z]{2,}$")
_URL_RE = re.compile(r"https?://\S+|mailto:\S+", re.IGNORECASE)
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PLACEHOLDER_TOKEN_RE = re.compile(r"<[A-Z][A-Z0-9_]*>")
_NON_PROSE_COMMAND_RE = re.compile(
    r"\\(?:url|href|email|author|affiliation|address|institution|institute|thanks|"
    r"cite|citet|citep|citealt|citealp|citenum|citeauthor|citeyear|label|ref|eqref|"
    r"autoref|cref|Cref|bibliography|bibliographystyle)\*?"
    r"(?:\[[^\]]*\]){0,2}(?:\{[^{}]*\})?",
    re.DOTALL,
)
_LATEX_ENV_TOKEN_RE = re.compile(r"\\(?:begin|end)\s*\{[^{}]+\}")
_LATEX_COMMAND_HEAD_RE = re.compile(r"\\[A-Za-z@]+\*?")


def find_long_english_prose_spans(text: str, *, min_words: int = 18) -> List[str]:
    normalized = text or ""
    if not normalized:
        return []

    normalized = _URL_RE.sub(" ", normalized)
    normalized = _EMAIL_RE.sub(" ", normalized)
    normalized = _NON_PROSE_COMMAND_RE.sub(" ", normalized)
    normalized = _LATEX_ENV_TOKEN_RE.sub(" ", normalized)
    normalized = _PLACEHOLDER_TOKEN_RE.sub(" ", normalized)
    normalized = _LATEX_COMMAND_HEAD_RE.sub(" ", normalized)
    normalized = normalized.replace("{", " ").replace("}", " ")

    spans: List[str] = []
    current_words: List[str] = []
    span_start: Optional[int] = None
    span_end: Optional[int] = None
    previous_end: Optional[int] = None

    for match in _LONG_ENGLISH_WORD_RE.finditer(normalized):
        word = match.group(0)
        if _ALL_CAPS_ACRONYM_RE.fullmatch(word):
            continue

        gap = normalized[previous_end:match.start()] if previous_end is not None else ""
        if current_words and not _LONG_ENGLISH_GAP_RE.fullmatch(gap or " "):
            if len(current_words) >= min_words and span_start is not None and span_end is not None:
                spans.append(normalized[span_start:span_end].strip())
            current_words = []
            span_start = None
            span_end = None

        if not current_words:
            span_start = match.start()
        current_words.append(word)
        span_end = match.end()
        previous_end = match.end()

    if len(current_words) >= min_words and span_start is not None and span_end is not None:
        spans.append(normalized[span_start:span_end].strip())

    return [span for span in spans if span]


def classify_error(error_report: Dict[str, Any]) -> str:
    """
    Classify validation error into A/B/C1/C2 types.
    
    Type A: Resource/config missing (e.g., files not found)
           -> Handle with degradation, don't interrupt flow
    Type B: Recoverable syntax errors (e.g., unescaped special chars)
           -> Allow one translation retry
    Type C1: Structural errors - Local/Contained
            -> Single placeholder loss or isolated math mismatch (no global issue)
            -> Allow exactly 1 targeted LLM retry with restoration instructions
    Type C2: Structural errors - Global/Structural
            -> Multiple placeholder losses, global stack mismatch, or env collapse
            -> Deterministic fix only - NO LLM retry
    
    Args:
        error_report: Error report dictionary with command_error, ph_error, bracket_error
        
    Returns:
        Error type string: "A", "B", "C1", or "C2"
    """
    command_error = str(error_report.get("command_error", ""))
    ph_error = str(error_report.get("ph_error", ""))
    bracket_error = str(error_report.get("bracket_error", ""))
    math_error = str(error_report.get("math_error", ""))
    global_ph_error = str(error_report.get("global_ph_error", ""))
    
    all_errors = command_error + ph_error + bracket_error + math_error + global_ph_error
    
    # Type A: Resource/configuration missing
    if "not found" in all_errors.lower():
        return ERROR_TYPE_A
    
    # -------------------------------------------------------------------------
    # Determine if this is a structural (C) error and C1 or C2.
    # -------------------------------------------------------------------------

    # C2 trigger: Global placeholder stack mismatch -> always C2
    if global_ph_error:
        return ERROR_TYPE_C2

    # Immutable placeholder mismatches are explicit structural signals.
    if "eqrow_placeholder_sequence_mismatch" in math_error:
        return ERROR_TYPE_C2
    if "item_anchor_sequence_mismatch" in math_error:
        return ERROR_TYPE_C1
    if "list_env_item_order_mismatch" in math_error:
        return ERROR_TYPE_C1

    # Count expected/found mismatch occurrences across ALL error fields
    count_mismatches = re.findall(r"expected \d+, found \d+", all_errors)
    if count_mismatches:
        # Multiple distinct command mismatches -> C2 (structural collapse)
        if len(count_mismatches) > 1:
            return ERROR_TYPE_C2
        # Single command mismatch, no global stack error -> C1
        return ERROR_TYPE_C1

    # Count missing placeholders: C1 if exactly one, C2 if more
    if "Missing placeholders:" in ph_error:
        # Extract count of distinct missing placeholder names
        missing_section = ph_error.split("Missing placeholders:", 1)[1]
        # Each missing placeholder is separated by ", "
        missing_items = [p.strip() for p in missing_section.split(",") if p.strip()]
        # Filter to only real placeholder tokens (start with <)
        ph_tokens = [p for p in missing_items if p.startswith("<")]
        if len(ph_tokens) <= 1:
            return ERROR_TYPE_C1
        return ERROR_TYPE_C2

    # Math-mode delimiter mismatch (isolated, no global error) -> C1
    if "level_a_env_placeholder_residual" in math_error:
        return ERROR_TYPE_C2
    if "env_boundary_mismatch" in math_error:
        return ERROR_TYPE_C2
    if "env_restore_failed" in math_error:
        return ERROR_TYPE_C2

    # Math-mode delimiter mismatch (isolated, no global error) -> C1
    if "math_delimiter_mismatch" in math_error:
        return ERROR_TYPE_C1

    # Residual PROTECTED_CMD placeholder (isolated) -> C1
    if "protected_cmd_residual" in math_error:
        return ERROR_TYPE_C1

    # Dollar sign escaped by LLM (e.g., $x$ -> \$x\$) -> C1, allow one retry
    if "escaped_dollar_leak" in math_error:
        return ERROR_TYPE_C1

    # Type B: Default - recoverable errors (bracket issues, extra placeholders, etc.)
    return ERROR_TYPE_B





class ValidatorAgent(BaseToolAgent):
    def __init__(self, 
                 config: Dict[str, Any],
                 project_dir: str = None,
                 output_dir: str = None,
                 on_progress: Optional[Callable[[str, int, str], None]] = None
                 ):
        super().__init__(agent_name="ValidatorAgent", config=config, on_progress=on_progress)
        self.config = config
        self.project_dir = project_dir
        self.output_dir = output_dir
        self.code_like_filtered_bare_tokens = 0

    def execute(self, errors_report: Optional[List[Dict]] = None) -> List[Dict]:
        """
        Validate translated LaTeX content
        
        Args:
            errors_report: Optional previous error report to re-validate specific parts
            
        Returns:
            List of error reports for parts that failed validation
        """
        self.log(f"Starting validation for project: {os.path.basename(self.project_dir)}")
        self.update_progress(10, "Loading JSON maps")
        self.code_like_filtered_bare_tokens = 0
        
        sections = self.read_file(Path(self.output_dir, "sections_map.json"), "json")
        captions = self.read_file(Path(self.output_dir, "captions_map.json"), "json")
        envs = self.read_file(Path(self.output_dir, "envs_map.json"), "json")
        inputs_path = Path(self.output_dir, "inputs_map.json")
        inputs = self.read_file(inputs_path, "json") if inputs_path.exists() else []

        self.update_progress(30, "Extracting parts to validate")
        
        if errors_report is None:
            parts_need_val = self._extract_parts_need_validate(secs=sections,
                                                               caps=captions,
                                                               envs=envs)
        else:
            parts_need_val = self._extract_parts_from_report(secs=sections, 
                                                               caps=captions,
                                                               envs=envs,
                                                               errors_report=errors_report)
        
        self.update_progress(50, f"Validating {len(parts_need_val)} parts")
        
        errors_report = []
        for i, part in enumerate(parts_need_val):
            if i % 10 == 0:
                progress = 50 + int(40 * (i / len(parts_need_val)))
                self.update_progress(progress, f"Validating part {i+1}/{len(parts_need_val)}")
            
            error_report = self._validate(part)
            if error_report:
                errors_report.append(error_report)

        # Global placeholder stack validation for input begin/end tags.
        global_placeholder_errors = self._validate_global_input_placeholder_stack(
            sections=sections,
            inputs=inputs,
        )
        if global_placeholder_errors:
            errors_report.extend(global_placeholder_errors)

        # Always overwrite errors_report.json to avoid stale residual errors from
        # previous validation rounds.
        self.save_file(Path(self.output_dir, "errors_report.json"), "json", errors_report)

        if self.code_like_filtered_bare_tokens:
            self.log(
                f"Validator filtered {self.code_like_filtered_bare_tokens} bare math tokens in code-like spans",
                level="info",
            )

        self.update_progress(100, f"Validation complete: {len(errors_report)} errors found")
        self.log(f"Validation complete for {os.path.basename(self.project_dir)}, remaining errors: {len(errors_report)}")
        return errors_report

    def _validate(self, part: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate a single part (section/caption/environment)"""
        command_error = self._validate_command(part)
        ph_error = self._validate_placeholder(part)
        bracket_error = self._validate_closed_brackets(part)
        math_error = self._validate_math_delimiters(part)
        env_boundary_error = self._validate_env_boundaries(part)
        protected_cmd_error = self._validate_protected_cmd_residual(part)
        immutable_placeholder_error = self._validate_immutable_placeholders(part)
        list_structure_error = self._validate_list_item_structure(part)
        escaped_dollar_error = self._validate_escaped_dollar_leak(part)
        completeness_error = self._validate_long_english_prose(part)
        error_report = {}

        if (
            not command_error
            and not ph_error
            and not bracket_error
            and not math_error
            and not env_boundary_error
            and not protected_cmd_error
            and not immutable_placeholder_error
            and not list_structure_error
            and not escaped_dollar_error
            and not completeness_error
        ):
            return None
        else: 
            if "section" in part:
                error_report["part"] = "sec"
                error_report["num_or_ph"] = part["section"]
            elif "env_name" in part:
                error_report["part"] = "env"
                error_report["num_or_ph"] = part["placeholder"]
            elif "cap_type" in part:
                error_report["part"] = "cap"
                error_report["num_or_ph"] = part["placeholder"]

            if command_error:
                error_report["command_error"] = command_error
            if ph_error:
                error_report["ph_error"] = ph_error
            if bracket_error:
                error_report["bracket_error"] = bracket_error
            # Merge math and protected_cmd errors into math_error field
            math_issues = [
                e
                for e in [
                    math_error,
                    env_boundary_error,
                    protected_cmd_error,
                    immutable_placeholder_error,
                    list_structure_error,
                    escaped_dollar_error,
                ]
                if e
            ]
            if math_issues:
                error_report["math_error"] = "\n".join(math_issues)
            if completeness_error:
                error_report["completeness_error"] = completeness_error
            
            # Add error classification (A/B/C) for targeted handling
            error_report["error_type"] = classify_error(error_report)

        return error_report

    def _validate_command(self, part: Dict[str, Any]) -> Optional[str]:
        """Validate LaTeX commands are preserved in translation"""
        content = part.get("content", "")
        trans = part.get("trans_content") or ""

        src_counter = self.extract_command_counts(content)
        trans_counter = self.extract_command_counts(trans)
        
        if src_counter == trans_counter:
            return None

        errors = []
        for elem, count in src_counter.items():
            match = re.findall(re.escape(elem), trans)
            if len(match) < count:
                errors.append(f"'{elem}' — expected {count}, found {len(match)}")

        if errors:
            return "LaTeX command translation error or is missing:\n" + "\n".join(errors)
        return None        

    def _validate_placeholder(self, part: Dict[str, Any]) -> Optional[str]:
        """Validate placeholders are preserved in translation"""
        original_placeholders = self._extract_placeholders(part.get("content") or "")
        translated_placeholders = self._extract_placeholders(part.get("trans_content") or "")
        missing = original_placeholders - translated_placeholders
        extra = translated_placeholders - original_placeholders
        errors = []
        
        if missing:
            errors.append(f"Missing placeholders: {', '.join(sorted(missing))} translation error or is missing!") 
        if extra:
            errors.append(f"Extra placeholders: {', '.join(sorted(extra))} translation error or is redundant")
        
        return "\n".join(errors) if errors else None
        
    def _validate_escaped_dollar_leak(self, part: Dict[str, Any]) -> Optional[str]:
        """Detect when LLM incorrectly escaped $ as \\$ outside math context.
        
        The LLM sometimes mistakes inline math delimiters for currency symbols
        and escapes them: $x^2$ becomes \\$x^2\\$.  This produces 'Missing $
        inserted' errors during LaTeX compilation.  Comparing the count of
        literal ``\\$`` in the translation against the original is a reliable
        symptom check.
        """
        trans = part.get("trans_content") or ""
        # Fast exit: if there is no escaped dollar in the translation, no problem.
        if r"\$" not in trans:
            return None

        orig = part.get("content") or ""
        # Count raw `\$` occurrences using a simple str.count — no false positives.
        orig_escaped = orig.count(r"\$")
        trans_escaped = trans.count(r"\$")

        if trans_escaped > orig_escaped:
            excess = trans_escaped - orig_escaped
            return (
                f"escaped_dollar_leak: translation contains {excess} extra"
                f" \\$ (LLM escaped inline math delimiters as currency signs)"
            )
        return None

    def _validate_closed_brackets(self, part: Dict[str, Any]) -> Optional[str]:
        """Validate brackets are properly closed"""
        content = part.get("content") or ""
        trans_content = part.get("trans_content") or ""
        org_errors = self._find_brackets_errors(content, org=1)
        errors = self._find_brackets_errors(trans_content)

        if errors and not org_errors:
            return "Brackets error:\n" + "\n".join(errors)
        else:
            return None
        
    # ------------------------------------------------------------------ #
    # Math-mode delimiter validation & repair (Task 1)                    #
    # ------------------------------------------------------------------ #

    # Bare math tokens that are illegal in text mode
    _BARE_MATH_TOKEN_RE = re.compile(
        r'(?<!\\)(?:_|\^)'
        r'|(?<!\\)\\(?:frac|sum|int|prod|sqrt|alpha|beta|gamma|delta|epsilon'
        r'|theta|lambda|mu|nu|pi|sigma|tau|omega|Omega|infty|partial|nabla|cdot'
        r'|cdots|ldots|times|pm|mp|leq|geq|neq|approx|sim|simeq|equiv'
        r'|subseteq|supseteq|subset|supset|in|notin|forall|exists)'
        r'(?![A-Za-z])'
    )
    _PLACEHOLDER_RE = re.compile(r'<PLACEHOLDER_[^>]+>')
    _MATH_PLACEHOLDER_RE = re.compile(r'<INLMATH_[^>]+>')
    _ENV_PLACEHOLDER_RE = re.compile(r'<ENV(?:_BEGIN|_END)?_[^>]+>')
    _ITEM_PLACEHOLDER_RE = re.compile(r'<ITEM_[^>]+>')
    _EQROW_PLACEHOLDER_RE = re.compile(r'<EQROW_[^>]+>')

    @staticmethod
    def _extract_math_regions(text: str) -> List[tuple]:
        """
        Extract all math regions bounded by $, $$, \[, \( or \begin{math_env}.
        Returns list of (start, end, is_display) tuples.
        """
        regions = []
        # Pattern components
        pat_display_dollar = r'(?<!\\)\$\$.*?(?<!\\)\$\$'
        pat_inline_dollar = r'(?<!\$)\$(?!\$).*?(?<!\\)\$(?!\$)'
        pat_display_bracket = r'(?<!\\)\\\[.*?(?<!\\)\\\]'
        pat_inline_paren = r'(?<!\\)\\\(.*?(?<!\\)\\\)'
        pat_env = r'\\begin\{(equation\*?|align\*?|multline\*?|gather\*?|math|displaymath|eqnarray\*?)\}.*?\\end\{\1\}'
        
        regex = re.compile(f'{pat_display_dollar}|{pat_inline_dollar}|{pat_display_bracket}|{pat_inline_paren}|{pat_env}', re.DOTALL)
        
        for m in regex.finditer(text):
            matched_text = m.group(0)
            is_display = matched_text.startswith('$$') or matched_text.startswith(r'\[') or matched_text.startswith(r'\begin')
            regions.append((m.start(), m.end(), is_display))
            
        return regions

    @staticmethod
    def _extract_placeholder_spans(text: str) -> List[tuple]:
        """Extract [start, end) spans for placeholders like <PLACEHOLDER_...>."""
        return [(m.start(), m.end()) for m in ValidatorAgent._PLACEHOLDER_RE.finditer(text)]

    @staticmethod
    def _extract_math_placeholder_spans(text: str) -> List[tuple]:
        """Extract [start, end) spans for inline-math placeholders."""
        return [(m.start(), m.end()) for m in ValidatorAgent._MATH_PLACEHOLDER_RE.finditer(text)]

    @staticmethod
    def _extract_env_placeholder_spans(text: str) -> List[tuple]:
        """Extract [start, end) spans for environment placeholders."""
        return [(m.start(), m.end()) for m in ValidatorAgent._ENV_PLACEHOLDER_RE.finditer(text)]

    @staticmethod
    def _extract_item_placeholder_spans(text: str) -> List[tuple]:
        """Extract [start, end) spans for list item placeholders."""
        return [(m.start(), m.end()) for m in ValidatorAgent._ITEM_PLACEHOLDER_RE.finditer(text)]

    @staticmethod
    def _extract_eqrow_placeholder_spans(text: str) -> List[tuple]:
        """Extract [start, end) spans for eqnarray row placeholders."""
        return [(m.start(), m.end()) for m in ValidatorAgent._EQROW_PLACEHOLDER_RE.finditer(text)]

    @staticmethod
    def _extract_safe_command_arg_spans(text: str) -> List[tuple]:
        """
        Extract first-level {...} argument spans for safe cross-reference commands.
        Underscores inside these arguments are valid text keys, not math leakage.
        """
        safe_cmd_re = re.compile(
            r'\\(?:ref|eqref|label|pageref|autoref|cite|citet|citep|citealt|Cref|cref)\*?\s*\{'
        )
        spans: List[tuple] = []

        for m in safe_cmd_re.finditer(text):
            brace_start = m.end() - 1
            depth = 0
            i = brace_start
            while i < len(text):
                ch = text[i]
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        spans.append((brace_start + 1, i))
                        break
                i += 1

        return spans

    @staticmethod
    def _extract_code_like_spans(text: str) -> List[tuple]:
        """
        Extract spans that are code-like (tikz/pgfplots style regions).

        Bare `_`/`^` tokens in these spans are often valid plotting syntax and
        should not be treated as leaked math delimiters.
        """
        if not text:
            return []

        spans: List[tuple] = []

        env_re = re.compile(
            r'\\begin\{(?:tikzpicture|axis|semilogyaxis|loglogaxis|groupplot)\*?\}.*?'
            r'\\end\{(?:tikzpicture|axis|semilogyaxis|loglogaxis|groupplot)\*?\}',
            re.DOTALL,
        )
        for m in env_re.finditer(text):
            spans.append((m.start(), m.end()))

        # Typical pgfplots commands where `_` and `^` are data/expression syntax.
        line_cmd_re = re.compile(r'\\(?:addplot\+?|addplot3\+?|addlegendimage)(?![A-Za-z])')
        for m in line_cmd_re.finditer(text):
            line_end = text.find("\n", m.start())
            if line_end == -1:
                line_end = len(text)
            spans.append((m.start(), line_end))

        # Commands with structured argument blocks.
        head_cmd_re = re.compile(r'\\(?:pgfmathparse|pgfplotstableread|pgfplotsset|tikzset)(?![A-Za-z])')

        def _consume_balanced(src: str, start: int, open_ch: str, close_ch: str) -> int:
            if start >= len(src) or src[start] != open_ch:
                return start
            depth = 0
            i = start
            while i < len(src):
                ch = src[i]
                if ch == "\\":
                    i += 2
                    continue
                if ch == open_ch:
                    depth += 1
                elif ch == close_ch:
                    depth -= 1
                    if depth == 0:
                        return i + 1
                i += 1
            return len(src)

        for m in head_cmd_re.finditer(text):
            i = m.end()
            while i < len(text):
                while i < len(text) and text[i].isspace():
                    i += 1
                if i < len(text) and text[i] == "[":
                    i = _consume_balanced(text, i, "[", "]")
                    continue
                break

            if i < len(text) and text[i] == "{":
                end = _consume_balanced(text, i, "{", "}")
            else:
                line_end = text.find("\n", m.start())
                end = len(text) if line_end == -1 else line_end
            spans.append((m.start(), end))

        return spans

    @staticmethod
    def _index_in_spans(index: int, spans: List[tuple]) -> bool:
        """Check whether an index belongs to any [start, end) span."""
        for s, e in spans:
            if s <= index < e:
                return True
        return False

    def _validate_math_delimiters(self, part: Dict[str, Any]) -> Optional[str]:
        """Validate that translation preserves math-mode delimiters.

        Checks that:
        1. The number of $ delimiters in translation >= original.
        2. No bare math tokens (_^\\frac etc.) appear outside $...$ in translation
           when the original has them inside $...$.

        Returns error string with 'math_delimiter_mismatch' if issue detected.
        """
        original = part.get("content") or ""
        translated = part.get("trans_content") or ""
        if not original or not translated:
            return None

        # Count $ characters (rough check, exclude $$)
        def _count_inline_dollars(text: str) -> int:
            # Count standalone $ (not part of $$)
            return len(re.findall(r'(?<!\$)\$(?!\$)', text))

        orig_dollars = _count_inline_dollars(original)
        trans_dollars = _count_inline_dollars(translated)

        errors = []
        if trans_dollars < orig_dollars:
            errors.append(
                f"math_delimiter_mismatch: original has {orig_dollars} inline $, "
                f"translation has {trans_dollars}"
            )

        # Check for bare math tokens outside $ in translation when original has them inside $
        orig_regions = self._extract_math_regions(original)
        if orig_regions:
            # Build a mask of positions inside math environments in translation
            trans_regions = self._extract_math_regions(translated)
            placeholder_spans = self._extract_placeholder_spans(translated)
            math_placeholder_spans = self._extract_math_placeholder_spans(translated)
            env_placeholder_spans = self._extract_env_placeholder_spans(translated)
            item_placeholder_spans = self._extract_item_placeholder_spans(translated)
            eqrow_placeholder_spans = self._extract_eqrow_placeholder_spans(translated)
            safe_arg_spans = self._extract_safe_command_arg_spans(translated)
            code_like_spans = self._extract_code_like_spans(translated)
            inside = set()
            for s, e, _ in trans_regions:
                inside.update(range(s, e))

            filtered_code_like_tokens = 0
            for m in self._BARE_MATH_TOKEN_RE.finditer(translated):
                if self._index_in_spans(m.start(), placeholder_spans):
                    continue
                if self._index_in_spans(m.start(), math_placeholder_spans):
                    continue
                if self._index_in_spans(m.start(), env_placeholder_spans):
                    continue
                if self._index_in_spans(m.start(), item_placeholder_spans):
                    continue
                if self._index_in_spans(m.start(), eqrow_placeholder_spans):
                    continue
                if self._index_in_spans(m.start(), safe_arg_spans):
                    continue
                if self._index_in_spans(m.start(), code_like_spans):
                    filtered_code_like_tokens += 1
                    continue
                if m.start() not in inside:
                    errors.append(
                        f"math_delimiter_mismatch: bare math token '{m.group()}' "
                        f"at pos {m.start()} is outside $...$ in translation"
                    )
                    break  # One sample is enough to trigger repair

            if filtered_code_like_tokens:
                self.code_like_filtered_bare_tokens += filtered_code_like_tokens

            # Severe corruption checks within translated math regions
            for s, e, _ in trans_regions:
                math_text = translated[s:e]
                # Check for unbalanced latex literal braces \{ and \}
                left_braces = len(re.findall(r'\\\{', math_text))
                right_braces = len(re.findall(r'\\\}', math_text))
                if left_braces != right_braces:
                    errors.append(f"math_delimiter_mismatch: structural corruption detected (unbalanced \\{{ \\}}) in math block: {math_text[:40]}...")
                    break
                    
                # Check for massive English leakage (more than 3 consecutive words not in \text or similar)
                # Quick heuristic: if we find 3 consecutive space-separated purely alphabetical words > 2 chars each
                # This catches things like "$g$ fixes $x$" fused inside a math block incorrectly.
                # But be careful not to trigger on valid math text.
                # We will rely primarily on the unbalanced braces for now, as it covers the most severe destruction
                # we've seen (e.g., `\\} = 0$`).

        return "\n".join(errors) if errors else None

    def _validate_env_boundaries(self, part: Dict[str, Any]) -> Optional[str]:
        """Validate ENV placeholders are fully restored and boundary tags are balanced."""
        translated = part.get("trans_content") or ""
        if not translated:
            return None

        if "<ENV_RESTORE_FAILED>" in translated:
            return "env_boundary_mismatch: env_restore_failed marker detected"

        level_a_residual = re.findall(r'<ENV_\d+>', translated)
        if level_a_residual:
            return (
                "level_a_env_placeholder_residual: unresolved Level-A ENV placeholders: "
                + ", ".join(level_a_residual[:5])
            )

        token_re = re.compile(r'<ENV_(BEGIN|END)_(\d+)>')
        tokens = list(token_re.finditer(translated))
        if not tokens:
            return None

        stack: List[str] = []
        for m in tokens:
            kind = m.group(1)
            idx = m.group(2)
            if kind == "BEGIN":
                stack.append(idx)
            else:
                if not stack:
                    return f"env_boundary_mismatch: unexpected END token ENV_END_{idx}"
                top = stack.pop()
                if top != idx:
                    return (
                        "env_boundary_mismatch: crossed boundary tokens "
                        f"ENV_BEGIN_{top} ... ENV_END_{idx}"
                    )

        if stack:
            return (
                "env_boundary_mismatch: unclosed BEGIN token(s): "
                + ", ".join(f"ENV_BEGIN_{idx}" for idx in stack[:5])
            )
        return "env_boundary_mismatch: unresolved ENV_BEGIN/ENV_END placeholders remain"

    def _validate_immutable_placeholders(self, part: Dict[str, Any]) -> Optional[str]:
        """
        Validate ITEM/EQROW immutable placeholders are not dropped/reordered.

        For regular translated output, expected list is usually empty. This still
        catches residual placeholder leakage (found != expected).
        """
        original = part.get("content") or ""
        translated = part.get("trans_content") or ""
        if not translated:
            return None

        errors: List[str] = []
        expected_item = self._ITEM_PLACEHOLDER_RE.findall(original)
        item_error = validate_immutable_placeholder_sequence(translated, expected_item, "ITEM")
        if item_error:
            errors.append(item_error)

        expected_eqrow = self._EQROW_PLACEHOLDER_RE.findall(original)
        eqrow_error = validate_immutable_placeholder_sequence(translated, expected_eqrow, "EQROW")
        if eqrow_error:
            errors.append(eqrow_error)

        return "\n".join(errors) if errors else None

    def _validate_list_item_structure(self, part: Dict[str, Any]) -> Optional[str]:
        """Validate enumerate/itemize structure and item anchors for list environments."""
        env_name = str(part.get("env_name", "") or "").lower()
        if env_name not in {"enumerate", "enumerate*", "itemize", "itemize*"}:
            return None

        original = part.get("content") or ""
        translated = part.get("trans_content") or ""
        if not translated:
            return None

        _, _, src_tokens = anchor_list_items_in_env_body(original)
        _, _, tgt_tokens = anchor_list_items_in_env_body(translated)
        if len(src_tokens) != len(tgt_tokens):
            return (
                "list_env_item_order_mismatch: item count mismatch "
                f"(expected {len(src_tokens)}, found {len(tgt_tokens)})"
            )

        item_cmd_re = re.compile(r'\\item(?:\s*\[[^\]]*\])?')
        src_item_cmds = item_cmd_re.findall(original)
        tgt_item_cmds = item_cmd_re.findall(translated)
        if len(src_item_cmds) != len(tgt_item_cmds):
            return (
                "list_env_item_order_mismatch: item command count mismatch "
                f"(expected {len(src_item_cmds)}, found {len(tgt_item_cmds)})"
            )

        token_re = re.compile(
            r'\\begin\{(?:enumerate|itemize)\*?\}'
            r'|\\end\{(?:enumerate|itemize)\*?\}'
            r'|\\item(?:\s*\[[^\]]*\])?'
        )
        stack: List[str] = []
        for m in token_re.finditer(translated):
            token = m.group(0)
            if token.startswith(r"\begin{"):
                name = token[len(r"\begin{"):-1]
                stack.append(name)
                continue
            if token.startswith(r"\end{"):
                name = token[len(r"\end{"):-1]
                if not stack:
                    return "list_env_item_order_mismatch: unexpected list end token"
                top = stack.pop()
                if top != name:
                    return (
                        "list_env_item_order_mismatch: crossed list nesting "
                        f"(begin={top}, end={name})"
                    )
                continue
            if not stack:
                return "list_env_item_order_mismatch: item command outside list boundary"

        if stack:
            return "list_env_item_order_mismatch: unclosed list environment boundary"

        return None

    @staticmethod
    def repair_math_delimiters(original: str, translated: str) -> str:
        """Spec invariant: speculative math delimiter repair must be unreachable."""
        raise SpeculativeRepairForbiddenError(
            "forbidden: speculative repair in repair_math_delimiters"
        )

    def _validate_protected_cmd_residual(self, part: Dict[str, Any]) -> Optional[str]:
        """Check for unreplaced PROTECTED_CMD placeholders in translation."""
        translated = part.get("trans_content") or ""
        if re.search(r'PROTECTED_CMD_\d+', translated):
            return (
                "protected_cmd_residual: translation contains unreplaced "
                "PROTECTED_CMD placeholder — unmask restoration may have failed"
            )
        return None

    def _validate_long_english_prose(self, part: Dict[str, Any]) -> Optional[str]:
        if "section" not in part:
            return None
        section_id = str(part.get("section", ""))
        if section_id in {"-1", "0"}:
            return None

        translated = part.get("trans_content") or ""
        spans = find_long_english_prose_spans(translated, min_words=18)
        if not spans:
            return None

        sample = spans[0][:180]
        return (
            "long_english_prose_span: remaining English prose detected. "
            "Translate the residual English prose while keeping LaTeX commands, "
            f"placeholders, math, and structure shell unchanged. Sample: {sample}"
        )

    def _validate_global_input_placeholder_stack(self, sections: List[Dict], inputs: List[Dict]) -> List[Dict]:
        """Validate global begin/end placeholder stack for extracted \\input blocks."""
        if not sections or not inputs:
            return []

        begin_map = {}
        end_map = {}
        for item in inputs:
            begin = item.get("begin")
            end = item.get("end")
            if begin and end:
                begin_map[begin] = item
                end_map[end] = item

        if not begin_map or not end_map:
            return []

        section_ranges = []
        merged_parts = []
        cursor = 0
        for sec in sections:
            sec_id = str(sec.get("section"))
            content = sec.get("trans_content") or sec.get("content") or ""
            start = cursor
            merged_parts.append(content)
            cursor += len(content)
            section_ranges.append((start, cursor, sec_id))
            merged_parts.append("\n")
            cursor += 1
        merged_text = "".join(merged_parts)

        def _section_for_pos(pos: int) -> str:
            for start, end, sec_id in section_ranges:
                if start <= pos < end:
                    return sec_id
            if section_ranges:
                return section_ranges[-1][2]
            return "0"

        pattern = re.compile(r"<PLACEHOLDER_[^>]+?_begin>|<PLACEHOLDER_[^>]+?_end>")
        stack: List[tuple] = []
        section_issues: Dict[str, List[str]] = {}

        for match in pattern.finditer(merged_text):
            tag = match.group(0)
            sec_id = _section_for_pos(match.start())

            if tag in begin_map:
                stack.append((tag, sec_id))
                continue

            if tag in end_map:
                if not stack:
                    section_issues.setdefault(sec_id, []).append(
                        f"global_placeholder_stack_mismatch: unmatched end tag {tag}"
                    )
                    continue

                begin_tag, begin_sec_id = stack.pop()
                if end_map[tag] != begin_map.get(begin_tag):
                    msg = (
                        f"global_placeholder_stack_mismatch: mismatched tags "
                        f"{begin_tag} vs {tag}"
                    )
                    section_issues.setdefault(begin_sec_id, []).append(msg)
                    section_issues.setdefault(sec_id, []).append(msg)

        for begin_tag, begin_sec_id in stack:
            section_issues.setdefault(begin_sec_id, []).append(
                f"global_placeholder_stack_mismatch: unmatched begin tag {begin_tag}"
            )

        reports: List[Dict] = []
        for sec_id, issues in section_issues.items():
            reports.append(
                {
                    "part": "sec",
                    "num_or_ph": sec_id,
                    "global_ph_error": "\n".join(sorted(set(issues))),
                    "error_type": ERROR_TYPE_C,
                }
            )
        return reports

    def _find_brackets_errors(self, content, org=None):
        """Find unmatched brackets in content"""
        # Only check [] and {} - parentheses () cause false positives
        # with numbered lists like 1) 2) in enumerate environments
        bracket_pairs = {'[': ']', '{': '}'}
        
        opening_brackets = set(bracket_pairs.keys())
        closing_brackets = set(bracket_pairs.values())

        stack = []
        errors = []
        for idx, char in enumerate(content):
            if char in opening_brackets:
                stack.append((char, idx))
            elif char in closing_brackets:
                if not stack:
                    fragment = content[max(0, idx - 10): idx + 10]
                    errors.append(f"Extra closing bracket '{char}' at position {idx}, context: {fragment}")
                else:
                    last_open, open_idx = stack.pop()
                    if bracket_pairs[last_open] != char:
                        fragment = content[open_idx: idx + 1]
                        errors.append(f"Bracket mismatch: '{last_open}' opened at {open_idx} does not match '{char}' at {idx}, fragment: {fragment}")

        # Any unmatched opening brackets left in stack
        for open_bracket, pos in stack:
            fragment = content[pos: pos + 20]
            errors.append(f"Unmatched opening bracket '{open_bracket}' at position {pos}, fragment: {fragment}")

        return errors

    def extract_command_counts(self, latex_code: str) -> Counter:
        """Extract and count LaTeX commands using AST"""
        walker = LatexWalker(latex_code)
        nodes, _, _ = walker.get_latex_nodes()
        counter = Counter()
        
        ignored_commands = {'eg', 'ie'}

        def recurse(nodes):
            for node in nodes:
                clsname = node.__class__.__name__

                if clsname == "LatexMacroNode":
                    macro_name = node.macroname

                    if macro_name in ignored_commands:
                        continue
                    if len(macro_name) == 1 and not macro_name.isalpha():
                        continue

                    command = f"\\{macro_name}"
                    counter[command] += 1

                    if node.nodeargd:
                        for arg in node.nodeargd.argnlist:
                            if arg is not None:
                                recurse([arg])

                elif clsname == "LatexEnvironmentNode":
                    env_name = node.environmentname
                    counter[f"\\begin{{{env_name}}}"] += 1
                    recurse(node.nodelist)
                    counter[f"\\end{{{env_name}}}"] += 1

                elif hasattr(node, 'nodelist') and node.nodelist:
                    recurse(node.nodelist)

        recurse(nodes)
        return counter

    def _extract_placeholders(self, content):
        """Extract all placeholders from content"""
        input_pattern = re.compile(r"<PLACEHOLDER_[^>]+?_begin>|<PLACEHOLDER_[^>]+?_end>")
        placeholder_pattern_cap = re.compile(r"<PLACEHOLDER_CAP_\d+>")
        placeholder_pattern_env = re.compile(r"<PLACEHOLDER_ENV_\d+>")
        placeholders = set()
        for pattern in [input_pattern, placeholder_pattern_cap, placeholder_pattern_env]:
            placeholders.update(pattern.findall(content))
        return placeholders

    def _extract_parts_need_validate(self, secs, caps, envs):
        """Extract parts that need validation"""
        secs_need_val = [sec for sec in secs if sec["section"] != "0" and sec["section"] != "-1"]
        caps_need_val = caps
        
        if envs:
            if "need_trans" in envs[0]:
                envs_need_val = [env for env in envs if env["need_trans"]]
            else:
                envs_need_val = [env for env in envs if env["content"] != env["trans_content"]]
        else:
            envs_need_val = []

        return secs_need_val + caps_need_val + envs_need_val
    
    def _extract_parts_from_report(
        self,
        secs: List[Dict],
        caps: List[Dict],
        envs: List[Dict],
        errors_report: List[Dict]) -> List[Dict]:
        """Extract specific parts from error report for re-validation"""
        section_lookup = {s["section"]: s for s in secs}
        caption_lookup = {c["placeholder"]: c for c in caps}
        environment_lookup = {e["placeholder"]: e for e in envs}
        
        parts_to_validate = []
        
        for error in errors_report:
            part_type = error.get("part")
            identifier = error.get("num_or_ph")
            
            if not part_type or not identifier:
                continue
                
            part = None
            if part_type == "sec":
                part = section_lookup.get(identifier)
            elif part_type == "cap":
                part = caption_lookup.get(identifier)
            elif part_type == "env":
                part = environment_lookup.get(identifier)
            
            if part:
                parts_to_validate.append(part)
                
        return parts_to_validate

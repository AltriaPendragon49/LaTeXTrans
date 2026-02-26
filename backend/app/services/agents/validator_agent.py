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
from pathlib import Path
from collections import Counter
from pylatexenc.latexwalker import LatexWalker
import os
import re
import logging

logger = logging.getLogger(__name__)

# Error type constants
ERROR_TYPE_A = "A"  # Resource/config missing - handle with degradation
ERROR_TYPE_B = "B"  # Recoverable syntax errors - allow one retry
ERROR_TYPE_C = "C"  # Structural consistency errors - algorithmic fix required


def classify_error(error_report: Dict[str, Any]) -> str:
    """
    Classify validation error into A/B/C types.
    
    Type A: Resource/config missing (e.g., files not found)
           → Handle with degradation, don't interrupt flow
    Type B: Recoverable syntax errors (e.g., unescaped special chars)
           → Allow one translation retry
    Type C: Structural consistency errors (e.g., 'expected X, found Y')
           → Requires algorithmic fix, LLM retry won't help
    
    Args:
        error_report: Error report dictionary with command_error, ph_error, bracket_error
        
    Returns:
        Error type string: "A", "B", or "C"
    """
    command_error = str(error_report.get("command_error", ""))
    ph_error = str(error_report.get("ph_error", ""))
    bracket_error = str(error_report.get("bracket_error", ""))
    math_error = str(error_report.get("math_error", ""))
    
    all_errors = command_error + ph_error + bracket_error + math_error
    
    # Type A: Resource/configuration missing
    if "not found" in all_errors.lower():
        return ERROR_TYPE_A
    
    # Type C: Structural consistency errors (expected X, found Y pattern)
    # These are token count mismatches that can't be fixed by LLM retry
    if re.search(r"expected \d+, found \d+", all_errors):
        return ERROR_TYPE_C
    
    # Type C: Missing placeholders (structural issue)
    if "Missing placeholders:" in ph_error:
        return ERROR_TYPE_C

    # Type C: Math-mode delimiter mismatch (deterministic repair, no LLM retry)
    if "math_delimiter_mismatch" in math_error:
        return ERROR_TYPE_C

    # Type C: Residual PROTECTED_CMD placeholder (deterministic restore, no LLM retry)
    if "protected_cmd_residual" in math_error:
        return ERROR_TYPE_C
    
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
        
        sections = self.read_file(Path(self.output_dir, "sections_map.json"), "json")
        captions = self.read_file(Path(self.output_dir, "captions_map.json"), "json")
        envs = self.read_file(Path(self.output_dir, "envs_map.json"), "json")

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
        
        if errors_report:
            self.save_file(Path(self.output_dir, "errors_report.json"), "json", errors_report)

        self.update_progress(100, f"Validation complete: {len(errors_report)} errors found")
        self.log(f"Validation complete for {os.path.basename(self.project_dir)}, remaining errors: {len(errors_report)}")
        return errors_report

    def _validate(self, part: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate a single part (section/caption/environment)"""
        command_error = self._validate_command(part)
        ph_error = self._validate_placeholder(part)
        bracket_error = self._validate_closed_brackets(part)
        math_error = self._validate_math_delimiters(part)
        protected_cmd_error = self._validate_protected_cmd_residual(part)
        error_report = {}

        if not command_error and not ph_error and not bracket_error and not math_error and not protected_cmd_error:
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
            math_issues = [e for e in [math_error, protected_cmd_error] if e]
            if math_issues:
                error_report["math_error"] = "\n".join(math_issues)
            
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
        r'(?<!\\)(?:_|\^|(?:\\(?:frac|sum|int|prod|sqrt|alpha|beta|gamma|delta|epsilon'
        r'|theta|lambda|mu|nu|pi|sigma|tau|omega|Omega|infty|partial|nabla|cdot'
        r'|cdots|ldots|times|pm|mp|leq|geq|neq|approx|sim|simeq|equiv'
        r'|subseteq|supseteq|subset|supset|in|notin|forall|exists)))'
    )

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
            inside = set()
            for s, e, _ in trans_regions:
                inside.update(range(s, e))

            for m in self._BARE_MATH_TOKEN_RE.finditer(translated):
                if m.start() not in inside:
                    errors.append(
                        f"math_delimiter_mismatch: bare math token '{m.group()}' "
                        f"at pos {m.start()} is outside $...$ in translation"
                    )
                    break  # One sample is enough to trigger repair

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

    @staticmethod
    def repair_math_delimiters(original: str, translated: str) -> str:
        """
        Repair math-mode delimiter mismatches by copying $ patterns from original.

        Strategy:
        1. Extract all $ and $$ regions from the original.
        2. For each missing inline-math region: find the corresponding
           math content in the translation (by occurrence order) and wrap it.
        3. For each bare math token in translation not inside $: wrap the
           smallest span covering it with $...$.

        This is a deterministic structural repair (Type C), not LLM retry.
        """
        if not original or not translated:
            return translated

        # Extract inline $...$ contents from original (in order)
        inline_re = re.compile(r'(?<!\$)\$(?!\$)(.*?)(?<!\\)\$(?!\$)', re.DOTALL)
        orig_inline = inline_re.findall(original)
        trans_inline_matches = list(inline_re.finditer(translated))

        # If translation is missing $ regions, try to inject them
        if len(orig_inline) > len(trans_inline_matches):
            # Walk translation, find positions of bare math tokens and wrap them
            bare_token_re = re.compile(
                r'(?<!\\)(?:[_^]|(?:\\(?:frac|sqrt|sum|int|prod|alpha|beta|gamma'
                r'|delta|epsilon|theta|lambda|mu|nu|pi|sigma|tau|omega'
                r'|Omega|infty|partial|nabla|cdot|times|pm|leq|geq|neq'
                r'|approx|equiv|forall|exists|in|notin)))'
            )
            # Find all math regions to build exclusion mask
            existing_regions = ValidatorAgent._extract_math_regions(translated)
            inside = set()
            for s, e, _ in existing_regions:
                inside.update(range(s, e))

            result = translated
            offset = 0
            for match in bare_token_re.finditer(translated):
                if match.start() in inside:
                    continue
                # Wrap the token and surrounding word in $...$
                # Expand to include adjacent word characters and math chars
                s = match.start()
                e = match.end()
                # Expand left to include preceding letters/digits/backslash-word
                allowed_chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_^\\{}'
                while s > 0 and result[s - 1 + offset] in allowed_chars:
                    s -= 1
                    if s <= 0:
                        break
                # Find end of token group
                while e < len(result) and result[e + offset] in allowed_chars:
                    e += 1
                # Wrap
                span = result[s:e]
                wrapped = f'${span}$'
                result = result[:s] + wrapped + result[e:]
                inside.update(range(s, e + 2))  # +2 for the two $ chars
                offset += 2  # Two extra chars added
                # Removed break to iteratively fix ALL found math tokens in this run

            if result != translated:
                logger.info(
                    f"repair_math_delimiters: injected $ around bare math token"
                )
                return result

        # If occurrence counts match, just return unmodified
        return translated

    def _validate_protected_cmd_residual(self, part: Dict[str, Any]) -> Optional[str]:
        """Check for unreplaced PROTECTED_CMD placeholders in translation."""
        translated = part.get("trans_content") or ""
        if re.search(r'PROTECTED_CMD_\d+', translated):
            return (
                "protected_cmd_residual: translation contains unreplaced "
                "PROTECTED_CMD placeholder — unmask restoration may have failed"
            )
        return None

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

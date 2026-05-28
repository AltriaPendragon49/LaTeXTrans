"""
验证器 Agent

从原型系统适配而来，包含以下改动：
- 移除所有 Streamlit 依赖
- 添加进度回调机制
- 集成 Python logging
- 完全保留验证逻辑
"""

from typing import Dict, Any, List, Optional, Callable
from .base_tool_agent import BaseToolAgent
from .pipeline_invariants import SpeculativeRepairForbiddenError
from backend.app.models.config_models import is_origin_cli_parity_config
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

# 错误类型常量
ERROR_TYPE_A = "A"  # 资源/配置缺失 —— 降级处理
ERROR_TYPE_B = "B"  # 可恢复的语法错误 —— 允许一次重试
ERROR_TYPE_C = "C"  # 结构一致性错误 —— 需要算法修复（旧版别名）
ERROR_TYPE_C1 = "C1"  # 结构：局部/自包含 —— 允许 1 次 LLM 重试
ERROR_TYPE_C2 = "C2"  # 结构：全局/结构性 —— 不允许 LLM 重试

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
_NON_BODY_SOURCE_COMMAND_RE = re.compile(
    r"\\(?:documentclass|documentstyle|author|affiliation|address|institution|institute|thanks|"
    r"email|orcid|orcidlink|bibliography|bibliographystyle|bibitem|bibentry|usepackage|"
    r"RequirePackage|newcommand|renewcommand|providecommand|DeclareMathOperator|"
    r"DeclarePairedDelimiter|DeclareRobustCommand|DeclareUnicodeCharacter|newtheorem|"
    r"theoremstyle|numberwithin|usetikzlibrary|tikzstyle|pgfplotsset|lstset|lstdefinelanguage)\*?\b",
    re.IGNORECASE,
)
_REFERENCE_HINT_RE = re.compile(
    r"\b(?:doi|arxiv|proceedings|conference|journal|transactions|press|publisher|"
    r"vol\.?|no\.?|pp\.?|pages|etal|et al\.?)\b",
    re.IGNORECASE,
)
_REFERENCE_YEAR_RE = re.compile(r"\b(?:19|20)\d{2}[a-z]?\b")
_AUTHORISH_NAME_RE = re.compile(
    r"\b[A-Z][a-z]+(?:-[A-Z][a-z]+)?(?:\s+(?:[A-Z]\.){1,2})?\s+[A-Z][a-z]+(?:-[A-Z][a-z]+)?\b"
)


def find_long_english_prose_spans(text: str, *, min_words: int = 18) -> List[str]:
    """检测翻译文本中残留的长英文散文片段。

    通过过滤 LaTeX 命令、URL、邮箱和占位符等非正文内容，
    查找连续英文字母单词超过 min_words 的片段。

    Args:
        text: 要检查的翻译文本
        min_words: 触发检测的最小连续英文单词数

    Returns:
        检测到的英文片段列表
    """
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


def _is_front_matter_section(section_id: Any) -> bool:
    """判断是否为前页部分（section_id 为 "-1" 或 "0"）。"""
    normalized = str(section_id or "").strip()
    return normalized in {"-1", "0"} or normalized.startswith("-1_chunk_")


def _looks_like_reference_or_author_block(text: str) -> bool:
    """判断文本是否类似于参考文献或作者信息块（允许保留英文）。"""
    normalized = text or ""
    if not normalized:
        return False

    english_words = _LONG_ENGLISH_WORD_RE.findall(normalized)
    if len(english_words) < 12:
        return False

    if _REFERENCE_HINT_RE.search(normalized):
        return True

    years = _REFERENCE_YEAR_RE.findall(normalized)
    names = _AUTHORISH_NAME_RE.findall(normalized)
    separator_score = normalized.count(",") + normalized.count(";") + normalized.lower().count(" and ")
    sentence_count = normalized.count(".")

    if len(years) >= 2 and len(names) >= 2:
        return True
    if separator_score >= 4 and len(names) >= 3 and sentence_count <= len(names) + 3:
        return True
    return False


def _allows_non_body_english(part: Dict[str, Any]) -> bool:
    """判断某部分是否允许非正文英文（如前页、文档根、参考文献）。"""
    section_id = part.get("section")
    if _is_front_matter_section(section_id):
        return True
    if str(part.get("chunk_role") or "").strip() == "document_root":
        return True

    source = part.get("content") or ""
    if _NON_BODY_SOURCE_COMMAND_RE.search(source):
        return True

    translated = part.get("trans_content") or ""
    return _looks_like_reference_or_author_block(translated)


def classify_error(error_report: Dict[str, Any]) -> str:
    """
    将验证错误分类为 A/B/C1/C2 类型。

    类型 A: 资源/配置缺失（如文件未找到）
           -> 降级处理，不中断流程
    类型 B: 可恢复的语法错误（如未转义的特殊字符）
           -> 允许一次翻译重试
    类型 C1: 结构错误 - 局部/自包含
            -> 单个占位符丢失或孤立的数学模式不匹配（无全局问题）
            -> 允许恰好 1 次定向 LLM 重试及还原指令
    类型 C2: 结构错误 - 全局/结构性
            -> 多个占位符丢失、全局栈不匹配或环境折叠
            -> 仅允许确定性修复 —— 不允许 LLM 重试

    Args:
        error_report: 包含 command_error、ph_error、bracket_error 的错误报告字典

    Returns:
        错误类型字符串: "A"、"B"、"C1" 或 "C2"
    """
    command_error = str(error_report.get("command_error", ""))
    ph_error = str(error_report.get("ph_error", ""))
    bracket_error = str(error_report.get("bracket_error", ""))
    math_error = str(error_report.get("math_error", ""))
    global_ph_error = str(error_report.get("global_ph_error", ""))

    all_errors = command_error + ph_error + bracket_error + math_error + global_ph_error

    # 类型 A: 资源/配置缺失
    if "not found" in all_errors.lower():
        return ERROR_TYPE_A

    # -------------------------------------------------------------------------
    # 判断是否为结构（C）错误以及属于 C1 还是 C2。
    # -------------------------------------------------------------------------

    # C2 触发：全局占位符栈不匹配 -> 始终为 C2
    if global_ph_error:
        return ERROR_TYPE_C2

    # 不可变占位符不匹配是明确的结构信号。
    if "eqrow_placeholder_sequence_mismatch" in math_error:
        return ERROR_TYPE_C2
    if "item_anchor_sequence_mismatch" in math_error:
        return ERROR_TYPE_C1
    if "list_env_item_order_mismatch" in math_error:
        return ERROR_TYPE_C1

    # 统计所有错误字段中的 expected/found 不匹配出现次数
    count_mismatches = re.findall(r"expected \d+, found \d+", all_errors)
    if count_mismatches:
        # 多个不同的命令不匹配 -> C2（结构坍塌）
        if len(count_mismatches) > 1:
            return ERROR_TYPE_C2
        # 单个命令不匹配，无全局栈错误 -> C1
        return ERROR_TYPE_C1

    # 统计缺失的占位符：恰好一个为 C1，多个为 C2
    if "Missing placeholders:" in ph_error:
        # 提取不同缺失占位符名称的数量
        missing_section = ph_error.split("Missing placeholders:", 1)[1]
        # 每个缺失的占位符以 ", " 分隔
        missing_items = [p.strip() for p in missing_section.split(",") if p.strip()]
        # 仅过滤真实的占位符令牌（以 < 开头）
        ph_tokens = [p for p in missing_items if p.startswith("<")]
        if len(ph_tokens) <= 1:
            return ERROR_TYPE_C1
        return ERROR_TYPE_C2

    # 数学模式分隔符不匹配（孤立，无全局错误）-> C1
    if "level_a_env_placeholder_residual" in math_error:
        return ERROR_TYPE_C2
    if "env_boundary_mismatch" in math_error:
        return ERROR_TYPE_C2
    if "env_restore_failed" in math_error:
        return ERROR_TYPE_C2
    if "document_boundary_leak" in math_error:
        return ERROR_TYPE_C2

    # 数学模式分隔符不匹配（孤立，无全局错误）-> C1
    if "math_delimiter_mismatch" in math_error:
        return ERROR_TYPE_C1

    # 残留的 PROTECTED_CMD 占位符（孤立）-> C1
    if "protected_cmd_residual" in math_error:
        return ERROR_TYPE_C1

    # LLM 错误转义的美元符（如 $x$ -> \$x\$）-> C1，允许一次重试
    if "escaped_dollar_leak" in math_error:
        return ERROR_TYPE_C1

    # 类型 B: 默认 —— 可恢复错误（括号问题、额外占位符等）
    return ERROR_TYPE_B


class ValidatorAgent(BaseToolAgent):
    """验证器 Agent：验证翻译后的 LaTeX 内容，检测结构和内容错误。"""

    def __init__(self,
                 config: Dict[str, Any],
                 project_dir: str = None,
                 output_dir: str = None,
                 on_progress: Optional[Callable[[str, int, str], None]] = None
                 ):
        """初始化 ValidatorAgent。"""
        super().__init__(agent_name="ValidatorAgent", config=config, on_progress=on_progress)
        self.config = config
        self.project_dir = project_dir
        self.output_dir = output_dir
        self.code_like_filtered_bare_tokens = 0
        self.origin_cli_parity = is_origin_cli_parity_config(config)

    def execute(self, errors_report: Optional[List[Dict]] = None) -> List[Dict]:
        """
        验证已翻译的 LaTeX 内容。

        Args:
            errors_report: 可选的先前错误报告，用于重新验证特定部分

        Returns:
            验证失败部分的错误报告列表
        """
        self.log(f"Starting validation for project: {os.path.basename(self.project_dir)}")
        self.update_progress(10, "Loading JSON maps")
        self.code_like_filtered_bare_tokens = 0

        sections = self.read_file(Path(self.output_dir, "sections_map.json"), "json")
        captions = self.read_file(Path(self.output_dir, "captions_map.json"), "json")
        envs = self.read_file(Path(self.output_dir, "envs_map.json"), "json")
        inputs_path = Path(self.output_dir, "inputs_map.json")
        inputs = [] if self.origin_cli_parity else self.read_file(inputs_path, "json") if inputs_path.exists() else []

        self.update_progress(30, "Extracting parts to validate")

        if errors_report is None:
            if self.origin_cli_parity:
                parts_need_val = self._extract_parts_need_validate_origin_cli_parity(
                    secs=sections,
                    caps=captions,
                    envs=envs,
                )
            else:
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

        # 全局占位符栈验证：检查 input begin/end 标签。
        if not self.origin_cli_parity:
            global_placeholder_errors = self._validate_global_input_placeholder_stack(
                sections=sections,
                inputs=inputs,
            )
            if global_placeholder_errors:
                errors_report.extend(global_placeholder_errors)

        # 总是覆盖 errors_report.json，避免前轮验证的残留陈旧错误。
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
        """验证单个部分（section/caption/environment）。

        执行多种验证检查：命令完整性、占位符保留、括号匹配、
        数学模式分隔符、环境边界、不可变占位符等。
        """
        if self.origin_cli_parity:
            return self._validate_origin_cli_parity(part)

        command_error = self._validate_command(part)
        ph_error = self._validate_placeholder(part)
        bracket_error = self._validate_closed_brackets(part)
        math_error = self._validate_math_delimiters(part)
        env_boundary_error = self._validate_env_boundaries(part)
        protected_cmd_error = self._validate_protected_cmd_residual(part)
        immutable_placeholder_error = self._validate_immutable_placeholders(part)
        list_structure_error = self._validate_list_item_structure(part)
        escaped_dollar_error = self._validate_escaped_dollar_leak(part)
        document_boundary_error = self._validate_document_boundary_leak(part)
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
            and not document_boundary_error
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
            # 将数学和保护命令错误合并到 math_error 字段
            math_issues = [
                e
                for e in [
                    math_error,
                    env_boundary_error,
                    protected_cmd_error,
                    immutable_placeholder_error,
                    list_structure_error,
                    escaped_dollar_error,
                    document_boundary_error,
                ]
                if e
            ]
            if math_issues:
                error_report["math_error"] = "\n".join(math_issues)
            if completeness_error:
                error_report["completeness_error"] = completeness_error

            # 添加错误分类（A/B/C），供定向处理使用
            error_report["error_type"] = classify_error(error_report)

        return error_report

    def _validate_origin_cli_parity(self, part: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Origin CLI parity 模式的验证逻辑（精简版）。"""
        command_error = self._validate_command(part)
        ph_error = self._validate_placeholder_origin_cli_parity(part)
        bracket_error = self._validate_closed_brackets_origin_cli_parity(part)
        error_report = {}

        if not command_error and not ph_error and not bracket_error:
            return None

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

        return error_report

    def _validate_command(self, part: Dict[str, Any]) -> Optional[str]:
        """验证翻译后 LaTeX 命令是否完整保留。"""
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
        """验证占位符在翻译中是否保留。"""
        original_placeholders = self._extract_placeholders(part.get("content") or "")
        translated_placeholders = self._extract_placeholders(part.get("trans_content") or "")
        missing = sorted(set(original_placeholders) - set(translated_placeholders))
        extra = sorted(set(translated_placeholders) - set(original_placeholders))
        errors = []

        if original_placeholders != translated_placeholders:
            errors.append(
                "Placeholder sequence mismatch: "
                f"expected {original_placeholders}, found {translated_placeholders}"
            )
        if missing:
            errors.append(f"Missing placeholders: {', '.join(missing)} translation error or is missing!")
        if extra:
            errors.append(f"Extra placeholders: {', '.join(extra)} translation error or is redundant")

        return "\n".join(errors) if errors else None

    def _validate_placeholder_origin_cli_parity(self, part: Dict[str, Any]) -> Optional[str]:
        """Origin CLI parity 模式的占位符验证。"""
        original_placeholders = self._extract_placeholders_origin_cli_parity(part["content"])
        translated_placeholders = self._extract_placeholders_origin_cli_parity(part["trans_content"])
        missing = original_placeholders - translated_placeholders
        extra = translated_placeholders - original_placeholders
        errors = []
        if missing:
            errors.append(f"Missing placeholders: {', '.join(sorted(missing))} translation error or is missing!")
        if extra:
            errors.append(f"Extra placeholders: {', '.join(sorted(extra))} translation error or is redundant")
        return "\n".join(errors) if errors else None

    def _validate_escaped_dollar_leak(self, part: Dict[str, Any]) -> Optional[str]:
        """检测 LLM 是否在数学上下文之外错误地将 $ 转义为 \\$。

        LLM 有时会将内联数学分隔符误认为货币符号并对其进行转义：
        $x^2$ 变成 \\$x^2\\$。这会在 LaTeX 编译时产生 'Missing $ inserted' 错误。
        比较翻译中文字 `\\$` 的计数与原文是一个可靠的症状检查。
        """
        trans = part.get("trans_content") or ""
        # 快速退出：如果翻译中没有转义美元符，则没有问题。
        if r"\$" not in trans:
            return None

        orig = part.get("content") or ""
        # 使用简单的 str.count 统计原始的 `\$` 出现次数 —— 无假阳性。
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
        """验证括号是否正确闭合。"""
        content = part.get("content") or ""
        trans_content = part.get("trans_content") or ""
        org_errors = self._find_brackets_errors(content, org=1)
        errors = self._find_brackets_errors(trans_content)

        if errors and not org_errors:
            return "Brackets error:\n" + "\n".join(errors)
        else:
            return None

    def _validate_closed_brackets_origin_cli_parity(self, part: Dict[str, Any]) -> Optional[str]:
        """Origin CLI parity 模式的括号闭合验证。"""
        content = part.get("content", "")
        trans_content = part.get("trans_content", "")
        org_errors = self._find_brackets_errors_origin_cli_parity(content, org=1)
        errors = self._find_brackets_errors_origin_cli_parity(trans_content)

        if errors and not org_errors:
            return "Brackets error:\n" + "\n".join(errors)
        return None

    # ------------------------------------------------------------------ #
    # 数学模式分隔符验证与修复 (Task 1)                                    #
    # ------------------------------------------------------------------ #

    # 文本模式中非法的裸露数学标记
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
        提取所有由 $、$$、\\[、\\( 或 \\begin{math_env} 界定的数学区域。
        返回 (start, end, is_display) 元组列表。
        """
        regions = []
        # 模式组件
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
        """提取 <PLACEHOLDER_...> 占位符的 [start, end) 区间。"""
        return [(m.start(), m.end()) for m in ValidatorAgent._PLACEHOLDER_RE.finditer(text)]

    @staticmethod
    def _extract_math_placeholder_spans(text: str) -> List[tuple]:
        """提取内联数学占位符的 [start, end) 区间。"""
        return [(m.start(), m.end()) for m in ValidatorAgent._MATH_PLACEHOLDER_RE.finditer(text)]

    @staticmethod
    def _extract_env_placeholder_spans(text: str) -> List[tuple]:
        """提取环境占位符的 [start, end) 区间。"""
        return [(m.start(), m.end()) for m in ValidatorAgent._ENV_PLACEHOLDER_RE.finditer(text)]

    @staticmethod
    def _extract_item_placeholder_spans(text: str) -> List[tuple]:
        """提取列表项占位符的 [start, end) 区间。"""
        return [(m.start(), m.end()) for m in ValidatorAgent._ITEM_PLACEHOLDER_RE.finditer(text)]

    @staticmethod
    def _extract_eqrow_placeholder_spans(text: str) -> List[tuple]:
        """提取 eqnarray 行占位符的 [start, end) 区间。"""
        return [(m.start(), m.end()) for m in ValidatorAgent._EQROW_PLACEHOLDER_RE.finditer(text)]

    @staticmethod
    def _extract_safe_command_arg_spans(text: str) -> List[tuple]:
        """
        提取安全交叉引用命令的第一级 {...} 参数区间。
        这些参数中的下划线是有效的文本键，不是数学泄漏。
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
        提取代码类区间（TikZ/pgfplots 样式区域）。

        这些区间中的裸露 `_`/`^` 标记通常是有效的绘图语法，
        不应被视为泄漏的数学分隔符。
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

        # 典型的 pgfplots 命令，其中 `_` 和 `^` 是数据/表达式语法。
        line_cmd_re = re.compile(r'\\(?:addplot\+?|addplot3\+?|addlegendimage)(?![A-Za-z])')
        for m in line_cmd_re.finditer(text):
            line_end = text.find("\n", m.start())
            if line_end == -1:
                line_end = len(text)
            spans.append((m.start(), line_end))

        # 具有结构化参数块的命令。
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
        """检查某个索引是否属于任意 [start, end) 区间。"""
        for s, e in spans:
            if s <= index < e:
                return True
        return False

    def _validate_math_delimiters(self, part: Dict[str, Any]) -> Optional[str]:
        """验证翻译是否保留了数学模式分隔符。

        检查：
        1. 翻译中 $ 分隔符数量 >= 原文。
        2. 翻译中没有裸露的数学标记（_、^、\\frac 等）出现在 $...$ 之外，
           而原文中它们在 $...$ 之内。

        如果检测到问题，返回包含 'math_delimiter_mismatch' 的错误字符串。
        """
        original = part.get("content") or ""
        translated = part.get("trans_content") or ""
        if not original or not translated:
            return None

        # 统计 $ 字符（粗略检查，排除 $$）
        def _count_inline_dollars(text: str) -> int:
            # 统计独立的 $（非 $$ 的一部分）
            return len(re.findall(r'(?<!\$)\$(?!\$)', text))

        orig_dollars = _count_inline_dollars(original)
        trans_dollars = _count_inline_dollars(translated)

        errors = []
        if trans_dollars != orig_dollars:
            errors.append(
                f"math_delimiter_mismatch: original has {orig_dollars} inline $, "
                f"translation has {trans_dollars}"
            )

        # 检查翻译中 $ 之外的裸露数学标记（原文中它们在 $ 之内）
        orig_regions = self._extract_math_regions(original)
        if orig_regions:
            # 构建翻译中数学环境内部位置的掩码
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
                    break  # 一个样本就足以触发修复

            if filtered_code_like_tokens:
                self.code_like_filtered_bare_tokens += filtered_code_like_tokens

            # 翻译后数学区域内的严重损坏检查
            for s, e, _ in trans_regions:
                math_text = translated[s:e]
                # 检查不平衡的 latex 文字大括号 \{ 和 \}
                left_braces = len(re.findall(r'\\\{', math_text))
                right_braces = len(re.findall(r'\\\}', math_text))
                if left_braces != right_braces:
                    errors.append(f"math_delimiter_mismatch: structural corruption detected (unbalanced \\{{ \\}}) in math block: {math_text[:40]}...")
                    break

        return "\n".join(errors) if errors else None

    def _validate_env_boundaries(self, part: Dict[str, Any]) -> Optional[str]:
        """验证 ENV 占位符是否已完全还原且边界标签是否平衡。"""
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
        验证 ITEM/EQROW 不可变占位符未被丢弃或重排。

        对于常规翻译输出，期望列表通常为空。此检查仍然能捕获
        残留的占位符泄漏（found != expected）。
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
        """验证 enumerate/itemize 环境的结构和 item 锚点。"""
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
        """规范不变量：推测性数学分隔符修复必须不可达。"""
        raise SpeculativeRepairForbiddenError(
            "forbidden: speculative repair in repair_math_delimiters"
        )

    def _validate_protected_cmd_residual(self, part: Dict[str, Any]) -> Optional[str]:
        """检查翻译中是否存在未替换的 PROTECTED_CMD 占位符。"""
        translated = part.get("trans_content") or ""
        if re.search(r'PROTECTED_CMD_\d+', translated):
            return (
                "protected_cmd_residual: translation contains unreplaced "
                "PROTECTED_CMD placeholder -- unmask restoration may have failed"
            )
        return None

    def _validate_long_english_prose(self, part: Dict[str, Any]) -> Optional[str]:
        """检查翻译中是否残留长英文散文片段。"""
        if "section" not in part:
            return None
        if _allows_non_body_english(part):
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

    def _validate_document_boundary_leak(self, part: Dict[str, Any]) -> Optional[str]:
        """检查文档级边界令牌是否泄漏到节正文中。"""
        if "section" not in part:
            return None
        if str(part.get("chunk_role") or "") == "document_root":
            return None

        translated = part.get("trans_content") or ""
        if not translated:
            return None

        leading_shell = part.get("leading_structure_shell") or ""
        trailing_shell = part.get("trailing_structure_shell") or ""
        body = translated
        if leading_shell and body.startswith(leading_shell):
            body = body[len(leading_shell):]
        if trailing_shell and body.endswith(trailing_shell):
            body = body[: -len(trailing_shell)]

        if not re.search(r"\\(?:begin|end)\s*\{document\}", body):
            return None

        return (
            "document_boundary_leak: document-level boundary token leaked into section body. "
            "Remove duplicated \\begin{document}/\\end{document} from the translated body "
            "while keeping only the parser-owned structure shell."
        )

    def _validate_global_input_placeholder_stack(self, sections: List[Dict], inputs: List[Dict]) -> List[Dict]:
        """验证提取的 \\input 块的全局 begin/end 占位符栈。"""
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
        """查找内容中未匹配的括号。"""
        # 仅检查 [] 和 {} —— 圆括号 () 会产生假阳性，
        # 如 enumerate 环境中带编号的列表 1) 2)
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

        # 栈中剩余的所有未匹配开括号
        for open_bracket, pos in stack:
            fragment = content[pos: pos + 20]
            errors.append(f"Unmatched opening bracket '{open_bracket}' at position {pos}, fragment: {fragment}")

        return errors

    def _find_brackets_errors_origin_cli_parity(self, content, org=None):
        """Origin CLI parity 模式的括号检查。"""
        if org:
            bracket_pairs = {'[': ']', '{': '}'}
        else:
            bracket_pairs = {'(': ')', '[': ']', '{': '}'}

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

        for open_bracket, pos in stack:
            fragment = content[pos: pos + 20]
            errors.append(f"Unmatched opening bracket '{open_bracket}' at position {pos}, fragment: {fragment}")

        return errors

    def extract_command_counts(self, latex_code: str) -> Counter:
        """使用 AST 解析提取并统计 LaTeX 命令。"""
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
        """从内容中提取所有占位符。"""
        input_pattern = re.compile(r"<PLACEHOLDER_[^>]+?_begin>|<PLACEHOLDER_[^>]+?_end>")
        placeholder_pattern_cap = re.compile(r"<PLACEHOLDER_CAP_\d+>")
        placeholder_pattern_env = re.compile(r"<PLACEHOLDER_ENV_\d+>")
        placeholder_pattern_newcommand = re.compile(r"<PLACEHOLDER_NEWCOMMAND_\d+>")
        combined_pattern = re.compile(
            rf"{input_pattern.pattern}|{placeholder_pattern_cap.pattern}|"
            rf"{placeholder_pattern_env.pattern}|{placeholder_pattern_newcommand.pattern}"
        )
        placeholders = combined_pattern.findall(content)
        return placeholders

    def _extract_placeholders_origin_cli_parity(self, content):
        """Origin CLI parity 模式下提取占位符。"""
        input_pattern = re.compile(r"<PLACEHOLDER_[^>]+?_begin>|<PLACEHOLDER_[^>]+?_end>")
        placeholder_pattern_cap = re.compile(r"<PLACEHOLDER_CAP_\d+>")
        placeholder_pattern_env = re.compile(r"<PLACEHOLDER_ENV_\d+>")
        placeholders = set()
        for pattern in [input_pattern, placeholder_pattern_cap, placeholder_pattern_env]:
            placeholders.update(pattern.findall(content))
        return placeholders

    def _extract_parts_need_validate(self, secs, caps, envs):
        """提取需要验证的部分（section、caption、environment）。"""
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

    def _extract_parts_need_validate_origin_cli_parity(self, secs, caps, envs):
        """Origin CLI parity 模式下提取需要验证的部分。"""
        secs_need_val = [sec for sec in secs if sec["section"] != 0]
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
        """从错误报告中提取特定部分用于重新验证。"""
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

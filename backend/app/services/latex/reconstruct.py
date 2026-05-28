"""LaTeX 重建模块 —— 用于生产环境 origin CLI 兼容内核。"""
from __future__ import annotations

import logging
import os
import re
from typing import Any, Callable, Dict, List, Optional

from .utils import find_main_tex_file, get_command_pattern

logger = logging.getLogger(__name__)


def _add_ctex_package_origin_cli_parity(latex_code: str) -> str:
    """为 origin CLI 兼容模式添加 ctex 包以支持中文编译。"""
    if "\\usepackage[UTF8]{ctex}" in latex_code:
        return latex_code
    match = get_command_pattern(r"documentclass").search(latex_code)
    if not match:
        return latex_code
    position = match.end()
    return latex_code[:position] + "\n\\usepackage[UTF8]{ctex}\n" + latex_code[position:]


class LatexConstructor:
    """LaTeX 重建器 —— 将翻译后的各节、环境、标题、输入文件和新命令重组为完整文档。"""

    def __init__(
        self,
        sections: List[Dict[str, Any]],
        captions: List[Dict[str, Any]],
        envs: List[Dict[str, Any]],
        inputs: List[Dict[str, Any]],
        newcommands: List[Dict[str, Any]],
        output_latex_dir: str,
        target_language: str = "en",
        origin_cli_parity: bool = True,
    ):
        """初始化 LaTeX 重建器。

        Args:
            sections: 翻译后的各节列表
            captions: 翻译后的标题/图题列表
            envs: 翻译后的环境列表
            inputs: 输入文件占位符映射
            newcommands: 自定义命令定义列表
            output_latex_dir: 输出目录
            target_language: 目标语言代码
            origin_cli_parity: 是否启用 origin CLI 兼容模式
        """
        self.sections = sections
        self.captions = captions
        self.envs = envs
        self.inputs = inputs
        self.newcommands = newcommands
        self.output_latex_dir = output_latex_dir
        self.target_language = target_language
        self.origin_cli_parity = True

    def construct(self, on_progress: Optional[Callable[[str, int, str], None]] = None) -> None:
        """执行 LaTeX 文档重建流程。

        依次合并各节、还原环境、标题、新命令和输入文件占位符，
        最后写出完整的 .tex 文件。

        Args:
            on_progress: 可选的进度回调函数(stage, percentage, message)
        """
        logger.info("Starting LaTeX reconstruction")
        if on_progress:
            on_progress("reconstructing", 10, "Merging sections...")

        tex = self._merge_sections()
        tex = self._revert_envs(tex)
        tex = self._revert_captions(tex)
        tex = self._revert_newcommands(tex)
        self._revert_inputs(tex)

        if on_progress:
            on_progress("reconstructing", 100, "Reconstruction complete")
        logger.info("LaTeX reconstruction complete")

    def _merge_sections(self) -> str:
        """将所有翻译后的节合并为一个完整的 LaTeX 字符串。"""
        logger.debug("Merging %d sections", len(self.sections))
        return "".join(f"{section['trans_content']}\n" for section in self.sections)

    def _revert_envs(self, tex: str) -> str:
        """将环境占位符还原为翻译后的环境内容。"""
        logger.debug("Reverting %d environments", len(self.envs))
        for env in self.envs:
            tex = tex.replace(env["placeholder"], env["trans_content"])
        return tex

    def _revert_captions(self, tex: str) -> str:
        """将标题占位符还原为翻译后的标题内容。"""
        logger.debug("Reverting %d captions", len(self.captions))
        for caption in self.captions:
            tex = tex.replace(caption["placeholder"], caption["trans_content"])
        return tex

    def _revert_newcommands(self, tex: str) -> str:
        """将新命令占位符还原为原始定义内容。"""
        logger.debug("Reverting %d newcommands", len(self.newcommands))
        for newcommand in self.newcommands:
            placeholder = newcommand["placeholder"]
            if placeholder not in tex:
                logger.warning(
                    "Placeholder %s not found in tex during newcommand restoration",
                    placeholder,
                )
            else:
                tex = tex.replace(placeholder, newcommand["content"])
        return tex

    def _revert_inputs(self, tex: str) -> None:
        """将输入文件占位符还原，并将内部内容写出为独立的 .tex 文件。"""
        begin_map = {sec["begin"]: sec for sec in self.inputs}
        end_map = {sec["end"]: sec for sec in self.inputs}
        pattern = re.compile(r"<PLACEHOLDER_[^>]+?_begin>|<PLACEHOLDER_[^>]+?_end>")

        stack: list[tuple[str, int]] = []
        pos = 0

        while True:
            match = pattern.search(tex, pos)
            if not match:
                break

            tag = match.group()
            if tag in begin_map:
                stack.append((tag, match.start()))
                pos = match.end()
                continue

            if tag in end_map:
                if not stack:
                    raise ValueError(f"Unmatched end tag: {tag}")

                begin_tag, begin_pos = stack.pop()
                if end_map[tag] != begin_map[begin_tag]:
                    raise ValueError(f"Mismatched tags: {begin_tag} vs {tag}")

                input_info = begin_map[begin_tag]
                end_pos = match.end()
                inner_start = begin_pos + len(begin_tag)
                inner_end = match.start()
                inner_content = tex[inner_start:inner_end].strip()

                relative_path = input_info["path"]
                if not relative_path.endswith(".tex"):
                    relative_path += ".tex"
                output_path = os.path.join(self.output_latex_dir, relative_path)

                logger.debug("Writing input file: %s", output_path)
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(inner_content + "\n")

                tex = tex[:begin_pos] + input_info["command"] + tex[end_pos:]
                pos = begin_pos + len(input_info["command"])
                continue

            pos = match.end()

        if stack:
            unclosed_tags = [tag for tag, _ in stack]
            logger.warning("Unclosed begin placeholder(s) found and skipped: %s", unclosed_tags)

        residual_matches = re.findall(r"<PLACEHOLDER_[^>]*>", tex)
        if residual_matches:
            logger.warning("Residual placeholders found and removed: %s", residual_matches)
            tex = re.sub(r"<PLACEHOLDER_[^>]*>", "", tex)

        tex = _add_ctex_package_origin_cli_parity(tex)
        main_file_path = find_main_tex_file(self.output_latex_dir)
        if main_file_path and os.path.exists(main_file_path):
            with open(main_file_path, "w", encoding="utf-8") as f:
                f.write(tex)
            return

        logger.warning("No main.tex file found in %s, creating a new one", self.output_latex_dir)
        main_file_path = os.path.join(self.output_latex_dir, "main.tex")
        with open(main_file_path, "w", encoding="utf-8") as f:
            f.write(tex)

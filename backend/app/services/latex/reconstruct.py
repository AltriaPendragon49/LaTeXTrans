"""
LaTeX Reconstructor

Adapted from prototype system with:
- Python logging added
- Optional progress callback mechanism
- All functionality preserved
"""

from typing import List, Dict, Any, Optional, Callable
import os
import re
import logging
from .utils import *
from .utils import restore_mangled_placeholders

logger = logging.getLogger(__name__)


class LatexConstructor:
    def __init__(self, 
                 sections: List[Dict[str, Any]], 
                 captions: List[Dict[str, Any]], 
                 envs: List[Dict[str, Any]],
                 inputs: List[Dict[str, Any]],
                 newcommands: List[Dict[str, Any]],
                 output_latex_dir: str,
                 target_language: str = "en"
                 ):
        self.sections = sections
        self.captions = captions
        self.envs = envs
        self.inputs = inputs
        self.newcommands = newcommands
        self.output_latex_dir = output_latex_dir
        self.target_language = target_language

    def construct(self, on_progress: Optional[Callable[[str, int, str], None]] = None):
        """
        Construct the translated LaTeX project from the sections, envs, captions and inputs
        
        Args:
            on_progress: Optional callback function(stage, percentage, message)
        """
        logger.info("Starting LaTeX reconstruction")
        
        if on_progress:
            on_progress("reconstructing", 10, "Merging sections...")
        
        tex = self._merge_sections()
        
        if on_progress:
            on_progress("reconstructing", 30, "Restoring mangled placeholders...")
            
        tex = self._restore_mangled_placeholders(tex)
        
        if on_progress:
            on_progress("reconstructing", 40, "Reverting environments...")
        
        tex = self._revert_envs(tex)
        
        if on_progress:
            on_progress("reconstructing", 50, "Reverting captions...")
        
        tex = self._revert_captions(tex)
        
        if on_progress:
            on_progress("reconstructing", 70, "Reverting newcommands...")
        
        tex = self._revert_newcommands(tex)

        # Process japanese specific packages if needed
        # tex = self._comment_out_latex_packages_for_ja(tex)
        # tex = self._add_lualatex_option_to_documentclass_for_ja(tex)

        if on_progress:
            on_progress("reconstructing", 90, "Writing output files...")
        
        self._revert_inputs(tex)
        
        if on_progress:
            on_progress("reconstructing", 100, "Reconstruction complete")
        
        logger.info("LaTeX reconstruction complete")
    
    def _merge_sections(self) -> str:
        """Merge all the sections to a tex"""
        logger.debug(f"Merging {len(self.sections)} sections")
        tex = ""
        for section in self.sections:
            original = section.get("content", "")
            translated = section.get("trans_content") or original
            content = restore_sectioning_command_structure(original, translated)
            content = restore_display_math_delimiters(original, content)
            content = restore_display_math_shell_structure(original, content)
            content = restore_twopartpiecewise_commands(original, content)
            content = restore_inline_math_segments(original, content)
            content = restore_math_environment_blocks(original, content)
            content = restore_tag_commands(original, content)
            content = restore_label_commands(original, content)
            tex += content + "\n"
        return tex
        
    def _restore_mangled_placeholders(self, tex: str) -> str:
        """Find and fix placeholders that the LLM escaped."""
        expected_phs = []
        for env in self.envs:
            expected_phs.append(env["placeholder"])
        for cap in self.captions:
            expected_phs.append(cap["placeholder"])
        for cmd in self.newcommands:
            expected_phs.append(cmd["placeholder"])
        for inp in self.inputs:
            expected_phs.append(inp["begin"])
            expected_phs.append(inp["end"])
            
        return restore_mangled_placeholders(tex, expected_phs)

    def _revert_envs(self, tex: str) -> str:
        """Revert all the envs to tex"""
        logger.debug(f"Reverting {len(self.envs)} environments")
        for env in self.envs:
            placeholder = env["placeholder"]
            original = env.get("content", "")
            translated = env.get("trans_content") or original
            content = restore_display_math_delimiters(original, translated)
            content = restore_display_math_shell_structure(original, content)
            content = restore_twopartpiecewise_commands(original, content)
            content = restore_inline_math_segments(original, content)
            content = restore_math_environment_blocks(original, content)
            content = restore_tag_commands(original, content)
            content = restore_environment_structure(original, content)
            content = restore_label_commands(original, content)
            tex = tex.replace(placeholder, content)
        return tex
             
    def _revert_captions(self, tex: str) -> str:
        """Revert all the captions to tex"""
        logger.debug(f"Reverting {len(self.captions)} captions")
        for caption in self.captions:
            placeholder = caption["placeholder"]
            original = caption.get("content", "")
            translated = caption.get("trans_content") or original
            content = restore_caption_command_structure(original, translated)
            content = restore_display_math_delimiters(original, content)
            content = restore_display_math_shell_structure(original, content)
            content = restore_twopartpiecewise_commands(original, content)
            content = restore_inline_math_segments(original, content)
            content = restore_math_environment_blocks(original, content)
            content = restore_tag_commands(original, content)
            content = restore_label_commands(original, content)
            tex = tex.replace(placeholder, content)
        return tex                              
    
    def _revert_newcommands(self, tex: str) -> str:
        """Revert all the newcommands to tex"""
        logger.debug(f"Reverting {len(self.newcommands)} newcommands")
        for newcommand in self.newcommands:
            placeholder = newcommand["placeholder"]
            tex = tex.replace(placeholder, newcommand["content"])
        return tex
                                          
    def _revert_inputs(self, tex: str):
        """Revert input placeholders and write separate files"""
        begin_map = {sec["begin"]: sec for sec in self.inputs}
        end_map = {sec["end"]: sec for sec in self.inputs}
        pattern = re.compile(r"<PLACEHOLDER_[^>]+?_begin>|<PLACEHOLDER_[^>]+?_end>")

        stack = []
        pos = 0

        while True:
            match = pattern.search(tex, pos)
            if not match:
                break

            tag = match.group()

            if tag in begin_map:
                stack.append((tag, match.start()))
                pos = match.end()
            elif tag in end_map:
                if not stack:
                    logger.error(f"Unmatched end tag: {tag}")
                    raise ValueError(f"Unmatched end tag: {tag}")
                begin_tag, begin_pos = stack.pop()
                if end_map[tag] != begin_map[begin_tag]:
                    logger.error(f"Mismatched tags: {begin_tag} vs {tag}")
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
                
                logger.debug(f"Writing input file: {output_path}")
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(inner_content + "\n")

                tex = tex[:begin_pos] + input_info["command"] + tex[end_pos:]
                pos = begin_pos + len(input_info["command"])

            else:
                pos = match.end()

        if stack:
            unclosed_tags = [tag for tag, _ in stack]
            logger.warning(f"Unclosed begin placeholder(s) found and skipped: {unclosed_tags}")
            print(f"⚠️ Warning: Unclosed begin placeholder(s) found and skipped: {unclosed_tags}")
        
        residual_matches = re.findall(r"<PLACEHOLDER_[^>]*>", tex)
        if residual_matches:
            logger.warning(f"Residual placeholders found and removed: {residual_matches}")
            print(f"⚠️ Warning: Residual placeholders found and removed: {residual_matches}")
            tex = re.sub(r"<PLACEHOLDER_[^>]*>", "", tex)

        # Add language-specific packages based on target language
        main_file_path = find_main_tex_file(self.output_latex_dir)
        original_main_tex = ""
        if main_file_path and os.path.exists(main_file_path):
            try:
                with open(main_file_path, "r", encoding="utf-8", errors="replace") as f:
                    original_main_tex = f.read()
            except Exception as exc:
                logger.warning(f"Failed to read source main tex for tail restoration: {exc}")

        tex = restore_document_tail_structure(original_main_tex, tex)
        tex = add_cjk_package(tex, self.target_language, tex_file_path=main_file_path)

        if main_file_path and os.path.exists(main_file_path):
            logger.info(f"Writing main tex file: {main_file_path}")
            with open(main_file_path, "w", encoding="utf-8") as f:
                f.write(tex)
        else:
            logger.warning(f"No main.tex file found in {self.output_latex_dir}, creating a new one")
            print(f"⚠️ Warning: No main.tex file found in {self.output_latex_dir}, creating a new one.")
            main_file_path = os.path.join(self.output_latex_dir, "main.tex")
            with open(main_file_path, "w", encoding="utf-8") as f:
                f.write(tex)

    def _comment_out_latex_packages_for_ja(self, tex):
        """Comment out packages that conflict with Japanese typesetting"""
        packages_to_comment = [
            r'\usepackage[utf8]{inputenc}',
            r'\usepackage[T1]{fontenc}',
            r'\usepackage{times}',
            r'\usepackage{mathptmx}',
            r'\pdfoutput=1'
        ]
        
        lines = tex.splitlines()
        
        for i, line in enumerate(lines):
            stripped_line = line.strip()
            for package in packages_to_comment:
                if stripped_line.startswith(package) and not stripped_line.startswith('%'):
                    lines[i] = line.replace(package, f'% {package}')
                    break
        
        return '\n'.join(lines)        

    def _add_lualatex_option_to_documentclass_for_ja(self, tex):
        """Add lualatex option to documentclass for Japanese support"""
        import re
        
        pattern = re.compile(r'\\documentclass(?:\[([^\]]*)\])?(\{.*?\})')
        
        def replacer(match):
            options = match.group(1)
            class_name = match.group(2)
            
            if options:
                if 'lualatex' not in options:
                    new_options = options + ', lualatex'
                else:
                    new_options = options
                return f'\\documentclass[{new_options}]{class_name}'
            else:
                return f'\\documentclass[lualatex]{class_name}'
        
        modified_source = pattern.sub(replacer, tex)
        return modified_source

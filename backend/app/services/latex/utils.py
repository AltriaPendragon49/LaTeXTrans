"""
LaTeX Utilities for Web Backend

Complete adaptation from prototype system with:
- All Streamlit dependencies removed
- Python logging added
- sys.stderr redirection removed
- Full AST processing and LaTeX manipulation functionality preserved
"""

from pylatexenc.latexwalker import (
    LatexWalker, LatexMacroNode, LatexEnvironmentNode, LatexGroupNode, LatexCharsNode,
    LatexSpecialsNode, LatexMathNode
)
from pylatexenc.latex2text import LatexNodes2Text
import os
import re
import json
import zipfile
import tarfile
from typing import Any, Dict, List, Optional, Tuple
from tqdm import tqdm
import regex
import subprocess
import requests
from bs4 import BeautifulSoup
from typing import List, Optional
import time
import logging

logger = logging.getLogger(__name__)

# Regex pattern constants
options = r"\[[^\[\]]*?\]"
spaces = r"[ \t]*"
get_pattern_brace = lambda index: rf"\{{((?:[^{{}}]++|(?{index}))*+)\}}"


def get_pattern_command_full(name, n=None):
    """Generate regex pattern for LaTeX commands"""
    pattern = rf'\\({name})'
    if n is None:
        pattern += rf'{spaces}({options})?'
        n = 1
        begin_brace = 3
    else:
        begin_brace = 2
    for i in range(n):
        tmp = get_pattern_brace(i*2+begin_brace)
        pattern += rf'{spaces}({tmp})'
    if n == 0:
        pattern += r'(?=[^a-zA-Z])'
    return pattern


def extract_compressed_files(folder_path):
    """
    Traverse the given folder and extract all compressed files (zip, tar, tar.gz, etc.).
    After extraction, delete the source compressed files.
    
    Args:
        folder_path (str): Path to the folder containing compressed files.
    """
    for root, _, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            if zipfile.is_zipfile(file_path):
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    extract_path = os.path.join(root, file.replace('.zip', ''))
                    zip_ref.extractall(extract_path)
                    logger.info(f"Extracted {file} to {extract_path}")
                os.remove(file_path)
            elif tarfile.is_tarfile(file_path):
                with tarfile.open(file_path, 'r:*') as tar_ref:
                    extract_path = os.path.join(root, file.replace('.tar', '').replace('.gz', ''))
                    tar_ref.extractall(extract_path)
                    logger.info(f"Extracted {file} to {extract_path}")
                os.remove(file_path)


def get_profect_dirs(folder_path):
    """
    Get a list of all subdirectories in the given folder.
    
    Args:
        folder_path (str): Path to the folder.
    
    Returns:
        list: A list of subdirectory paths.
    """
    projects = []
    for d in os.listdir(folder_path):
        if os.path.isdir(os.path.join(folder_path, d)):
            project_path = os.path.join(folder_path, d)
            projects.append(project_path)
    return projects


def has_appendix(latex_code):
    """Check if LaTeX code contains appendix"""
    appendix_pattern = re.compile(r"\\appendix\b")
    return bool(appendix_pattern.search(latex_code))


def remove_appendix_content(latex_code):
    """Remove appendix content from LaTeX code"""
    appendix_pattern = re.compile(r"\\appendix\b.*?(?=\\end\{document\})", re.DOTALL)
    modified_code = appendix_pattern.sub("", latex_code)
    return modified_code


def extract_latex_nodes(tex):
    """Extract LaTeX AST nodes using pylatexenc"""
    walker = LatexWalker(tex)
    nodes, npos, nlen = walker.get_latex_nodes()
    return nodes


def extract_text_from_tex(tex):
    """Convert LaTeX to plain text"""
    text = LatexNodes2Text().latex_to_text(tex)
    return text


def extract_structure(nodes, depth=0):
    """
    Extract structural information from LaTeX nodes
    
    Args:
        nodes: LaTeX nodes from pylatexenc
        depth: Current depth in the tree
    
    Returns:
        Dictionary containing commands, environments, specials, and math
    """
    structure = {
        'command': [],
        'environment': [],
        'special': [],
        'math': []
    }

    for node in nodes:
        if isinstance(node, LatexMacroNode):
            structure['command'].append({'name': node.macroname, 'depth': depth})
            if node.nodeargd:
                sub_structure = extract_structure(node.nodeargd.argnlist, depth + 1)
                for key in sub_structure:
                    structure[key].extend(sub_structure[key])
        elif isinstance(node, LatexEnvironmentNode):
            structure['environment'].append({'name': node.envname, 'depth': depth})
            sub_structure = extract_structure(node.nodelist, depth + 1)
            for key in sub_structure:
                structure[key].extend(sub_structure[key])
        elif isinstance(node, LatexGroupNode):
            sub_structure = extract_structure(node.nodelist, depth + 1)
            for key in sub_structure:
                structure[key].extend(sub_structure[key])
        elif isinstance(node, LatexSpecialsNode):
            structure['special'].append({'chars': node.specials_chars, 'depth': depth})
        elif isinstance(node, LatexMathNode):
            structure['math'].append({'type': node.displaytype, 'depth': depth})
            sub_structure = extract_structure(node.nodelist, depth + 1)
            for key in sub_structure:
                structure[key].extend(sub_structure[key])

    return structure


def extract_title(latex_code):
    """Extract title from LaTeX code"""
    title_start = latex_code.find(r"\title{")
    if title_start == -1:
        title_start = latex_code.find(r"\title[")
    if title_start == -1:
        return "No title"
    
    brace_start = latex_code.find("{", title_start)
    if brace_start == -1:
        return "No title"
    
    stack = []
    for i in range(brace_start, len(latex_code)):
        if latex_code[i] == "{":
            stack.append(i)
        elif latex_code[i] == "}":
            stack.pop()
            if not stack:
                return latex_code[brace_start + 1:i].strip()

    return "No title"


def extract_abstract(latex_code):
    """Extract abstract from LaTeX code"""
    abstract_pattern = regex.compile(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", regex.DOTALL)
    match = abstract_pattern.search(latex_code)
    
    if match:
        abstract = match.group(1).strip()
        return abstract
    
    abstract_start = latex_code.find(r"\abstract{")
    if abstract_start == -1:
        return "No abstract"

    brace_start = latex_code.find("{", abstract_start)
    if brace_start == -1:
        return "No abstract"

    stack = []
    for i in range(brace_start, len(latex_code)):
        if latex_code[i] == "{":
            stack.append(i)
        elif latex_code[i] == "}":
            stack.pop()
            if not stack:
                return latex_code[brace_start + 1:i].strip()

    return "No abstract"


def extract_keywords(latex_code):
    """Extract keywords from LaTeX code"""
    keywords_pattern = regex.compile(r"\\keywords\{(?:\{([^{}]*)\}|([^{}]*))\}", regex.DOTALL)
    match = keywords_pattern.search(latex_code)
    keywords = match.group(1) or match.group(2) if match else None
    return keywords.strip() if keywords else None


def extract_sections(latex_code):
    """Split LaTeX code into before and after first section"""
    section_pattern = regex.compile(r"\\(section|chapter)\b")
    match = section_pattern.search(latex_code)
    if not match:
        return latex_code, ""
    
    section_index = match.start()
    before_section = latex_code[:section_index]
    after_section = latex_code[section_index:]
    return before_section, after_section


def extract_captions(latex_code):
    """Extract caption from LaTeX code"""
    caption_start = latex_code.find(r"\caption{")
    if caption_start == -1:
        caption_start = latex_code.find(r"\caption[")
    if caption_start == -1:
        return "No caption"
    
    brace_start = latex_code.find("{", caption_start)
    if brace_start == -1:
        return "No caption"
    
    stack = []
    for i in range(brace_start, len(latex_code)):
        if latex_code[i] == "{":
            stack.append(i)
        elif latex_code[i] == "}":
            stack.pop()
            if not stack:
                return latex_code[brace_start + 1:i].strip()

    return "No caption"


def replace_figures(latex_code):
    """Replace figure environments with placeholders"""
    figure_pattern = regex.compile(
        r"\\begin\{(figure\*?|wrapfigure|SCfigure|tikzpicture)\}.*?\\end\{\1\}",
        regex.DOTALL
    )
    
    def replace_match(match):
        figure_code = match.group(0)
        caption = extract_captions(figure_code)
        return f"<FIGURE: {caption}>"
    
    latex_code = figure_pattern.sub(replace_match, latex_code)
    return latex_code


def replace_tables(latex_code):
    """Replace table environments with placeholders"""
    table_pattern = regex.compile(
        r"\\begin\{(table\*?|tabular|tabularx|longtable)\}.*?\\end\{\1\}",
        regex.DOTALL
    )
    
    def replace_match(match):
        table_code = match.group(0)
        caption = extract_captions(table_code)
        return f"<TABLE: {caption}>"
    
    latex_code = table_pattern.sub(replace_match, latex_code)
    return latex_code


def replace_newcommand(newcommand, latex_code):
    """Replace custom LaTeX commands with their definitions"""
    command_name, n_arguments, content = newcommand
    pattern = regex.compile(get_pattern_command_full(command_name, n_arguments), regex.DOTALL)

    def replace_function(match):
        this_content = content
        name = match.group(1)
        assert re.match(command_name, name)
        for i in range(n_arguments):
            text = match.group(3 + i * 2)
            this_content = this_content.replace(f'#{i+1}', f' {text} ')
        return this_content

    return pattern.sub(replace_function, latex_code)


def process_newcommands(latex_code):
    """Process and expand all newcommand definitions"""
    
    def get_nonNone(*args):
        result = [arg for arg in args if arg is not None]
        assert len(result) == 1
        return result[0]

    pattern_newcommand = rf'\\(?:newcommand\*?|def|renewcommand){spaces}(?:\{{\\([a-zA-Z]+)\}}|\\([a-zA-Z]+)){spaces}(?:\[(\d)\])?{spaces}({get_pattern_brace(4)})'
    pattern = regex.compile(pattern_newcommand, regex.DOTALL)
    count = 0
    full_newcommands = []
    match = pattern.search(latex_code)
    
    while match:
        name1 = match.group(1)
        name2 = match.group(2)
        name = get_nonNone(name1, name2)
        n_arguments = match.group(3)
        if n_arguments is None:
            n_arguments = 0
        else:
            n_arguments = int(n_arguments)
        content = match.group(5)
        latex_code = latex_code.replace(match.group(), f'REPLACE_{count}_NEWCOMMAND')
        full_newcommands.append(match.group(0))
        latex_code = replace_newcommand((name, n_arguments, content), latex_code)
        count += 1
        match = pattern.search(latex_code)
    
    for i in range(count):
        latex_code = latex_code.replace(f'REPLACE_{i}_NEWCOMMAND', full_newcommands[i])
    return latex_code


def replace_href(latex_code):
    """Remove href commands, keeping only the text"""
    href_pattern = regex.compile(r"\\href\{[^{}]*\}\{(.*?)\}")
    latex_code = href_pattern.sub(r"\1", latex_code)
    return latex_code


def replace_includegraphics(latex_code):
    """Remove includegraphics commands"""
    includegraphics_pattern = regex.compile(r"\\includegraphics(?:\[[^\]]*\])?\{[^\}]*\}", regex.DOTALL)
    latex_code = includegraphics_pattern.sub("", latex_code)
    return latex_code


def process_latex_to_eva(latex_code):
    """Process LaTeX code for evaluation/extraction"""
    latex_code = replace_href(latex_code)
    latex_code = replace_includegraphics(latex_code)
    latex_code = process_newcommands(latex_code)
    before_section, after_section = extract_sections(latex_code)
    title = extract_title(before_section) if extract_title(before_section) else 'No title'
    abstract = extract_abstract(before_section) if extract_abstract(before_section) else 'No abstract'
    keywords = extract_keywords(before_section) if extract_keywords(before_section) else ''
    after_section = replace_figures(after_section)
    after_section = replace_tables(after_section)
    tex_to_eva = f"{title}\n\n{abstract}\n\n{keywords}\n\n{after_section}"
    return tex_to_eva


def delete_ph(text) -> str:
    """Delete placeholders from text"""
    pattern = r'§(\.§){0,2}'
    text = re.sub(pattern, '', text)
    placeholder_pattern = r"<.*?PLACEHOLDER.*?>"
    text = re.sub(placeholder_pattern, "", text).strip()
    text = text.replace('\n', ' ')
    text = re.sub(r' +', ' ', text)
    return text.strip()


def restore_display_math_delimiters(original: str, translated: str) -> str:
    """
    Restore display-math delimiters when model output rewrites "\\[...\\]" as "$$...$$".

    This applies a conservative fix:
    - Only runs when source contains "\\[" / "\\]" and translation is missing them.
    - Replaces unescaped "$$" tokens in order.
    - Never forces replacement when source has no "\\[" / "\\]".
    """
    if not original or not translated:
        return translated

    src_open = len(re.findall(r'(?<!\\)\\\[', original))
    src_close = len(re.findall(r'(?<!\\)\\\]', original))

    # No bracketed display-math in source: do nothing.
    if src_open == 0 and src_close == 0:
        return translated

    dst_open = len(re.findall(r'(?<!\\)\\\[', translated))
    dst_close = len(re.findall(r'(?<!\\)\\\]', translated))

    missing_open = max(0, src_open - dst_open)
    missing_close = max(0, src_close - dst_close)
    if missing_open == 0 and missing_close == 0:
        return translated

    # Convert in complete pairs only.
    budget_pairs = min(missing_open, missing_close)
    if budget_pairs <= 0:
        return translated

    token_pattern = re.compile(r'(?<!\\)\$\$')
    matches = list(token_pattern.finditer(translated))
    if not matches:
        return translated

    replace_count = min(len(matches), budget_pairs * 2)
    if replace_count < 2:
        return translated

    parts = []
    last_idx = 0
    replaced = 0
    for m in matches:
        parts.append(translated[last_idx:m.start()])
        if replaced < replace_count:
            parts.append(r"\[" if replaced % 2 == 0 else r"\]")
            replaced += 1
        else:
            parts.append("$$")
        last_idx = m.end()
    parts.append(translated[last_idx:])
    return "".join(parts)


def _has_malformed_display_math_shell(text: str) -> bool:
    """
    Detect malformed display-math delimiters in a conservative way.

    Checks:
    - unbalanced `\\[ ... \\]`
    - unbalanced `$$ ... $$`
    - mixed nested usage between bracketed display math and `$$`
    """
    if not text:
        return False

    bracket_depth = 0
    in_dollar_display = False
    i = 0
    n = len(text)

    while i < n:
        if text[i] == "%" and not _is_escaped(text, i):
            while i < n and text[i] != "\n":
                i += 1
            continue

        if text.startswith(r"\[", i) and not _is_escaped(text, i):
            if in_dollar_display:
                return True
            bracket_depth += 1
            i += 2
            continue

        if text.startswith(r"\]", i) and not _is_escaped(text, i):
            if bracket_depth == 0:
                return True
            bracket_depth -= 1
            i += 2
            continue

        if text.startswith("$$", i) and not _is_escaped(text, i):
            if bracket_depth > 0:
                return True
            in_dollar_display = not in_dollar_display
            i += 2
            continue

        i += 1

    return bracket_depth != 0 or in_dollar_display


def restore_display_math_shell_structure(original: str, translated: str) -> str:
    """
    Detect malformed display-math shells in translated content.

    Previously this function would revert to the original (English) text when
    malformed shells were detected.  This caused silent translation loss.
    Now we keep the translated content and only log a warning — a translated
    PDF with minor math-shell issues is preferable to untranslated content.
    """
    if not original or not translated:
        return translated

    if _has_malformed_display_math_shell(translated) and not _has_malformed_display_math_shell(original):
        logger.warning(
            "Detected malformed display-math shell in translated content; "
            "keeping translated content to preserve target language output"
        )
        # Do NOT revert to original — keep translated content
        return translated

    return translated


def restore_label_commands(original: str, translated: str) -> str:
    """
    Restore `\\label{...}` commands deterministically from source to translation.

    This protects cross-reference stability when label keys are mutated by LLM output.
    Strategy:
    - Replace translated labels with source labels by occurrence order.
    - If translated drops labels entirely, append missing source labels to the end.
    """
    if not original or not translated:
        return translated

    pattern = re.compile(r"\\label\s*\{[^}]*\}")
    original_labels = pattern.findall(original)
    if not original_labels:
        return translated

    translated_matches = list(pattern.finditer(translated))
    if not translated_matches:
        suffix = "\n" + "\n".join(original_labels)
        if translated.endswith("\n"):
            return translated + "\n".join(original_labels)
        return translated + suffix

    parts = []
    last = 0
    for i, m in enumerate(translated_matches):
        parts.append(translated[last:m.start()])
        if i < len(original_labels):
            parts.append(original_labels[i])
        else:
            parts.append(m.group(0))
        last = m.end()
    parts.append(translated[last:])

    restored = "".join(parts)
    if len(original_labels) > len(translated_matches):
        extras = original_labels[len(translated_matches):]
        if restored.endswith("\n"):
            restored += "\n".join(extras)
        else:
            restored += "\n" + "\n".join(extras)

    return restored


_DISPLAY_TAG_ENVS = {
    "equation",
    "equation*",
    "align",
    "align*",
    "alignat",
    "alignat*",
    "flalign",
    "flalign*",
    "gather",
    "gather*",
    "multline",
    "multline*",
    "eqnarray",
    "eqnarray*",
}


def _has_tag_outside_display_math_context(text: str) -> bool:
    """
    Return True if any `\\tag{...}` appears outside a display-math context.

    Supported display contexts:
    - `\\[ ... \\]`
    - `$$ ... $$`
    - common display math environments (equation/align/gather/etc.)
    """
    if not text or r"\tag" not in text:
        return False

    tag_positions = [m.start() for m in re.finditer(r"\\tag\*?\s*\{", text)]
    if not tag_positions:
        return False

    bracket_depth = 0
    in_dollar_display = False
    display_env_stack: List[str] = []
    tag_idx = 0
    i = 0
    n = len(text)

    while i < n:
        while tag_idx < len(tag_positions) and tag_positions[tag_idx] == i:
            if bracket_depth == 0 and (not in_dollar_display) and (not display_env_stack):
                return True
            tag_idx += 1

        if text[i] == "%" and not _is_escaped(text, i):
            while i < n and text[i] != "\n":
                i += 1
            continue

        if text.startswith(r"\[", i) and not _is_escaped(text, i):
            bracket_depth += 1
            i += 2
            continue

        if text.startswith(r"\]", i) and not _is_escaped(text, i):
            if bracket_depth > 0:
                bracket_depth -= 1
            i += 2
            continue

        if text.startswith("$$", i) and not _is_escaped(text, i):
            in_dollar_display = not in_dollar_display
            i += 2
            continue

        if text.startswith(r"\begin", i) and not _is_escaped(text, i):
            begin_match = re.match(r"\\begin\s*\{([^}]+)\}", text[i:])
            if begin_match:
                env_name = begin_match.group(1).strip()
                if env_name in _DISPLAY_TAG_ENVS:
                    display_env_stack.append(env_name)
                i += begin_match.end()
                continue

        if text.startswith(r"\end", i) and not _is_escaped(text, i):
            end_match = re.match(r"\\end\s*\{([^}]+)\}", text[i:])
            if end_match:
                env_name = end_match.group(1).strip()
                if env_name in _DISPLAY_TAG_ENVS:
                    for stack_idx in range(len(display_env_stack) - 1, -1, -1):
                        if display_env_stack[stack_idx] == env_name:
                            del display_env_stack[stack_idx]
                            break
                i += end_match.end()
                continue

        i += 1

    return False


def restore_tag_commands(original: str, translated: str) -> str:
    """
    Restore/remove `\\tag{...}` commands by source occurrence order.

    - If source has no `\\tag`, strip all translated tags (they are unsafe drift).
    - If source has tags, replace translated tags by order to keep consistency.
    - If translated drops all tags, append source tags at end instead of
      reverting to original (to preserve target-language translation).
    """
    if not original or not translated:
        return translated

    pattern = re.compile(r"\\tag\*?\s*\{[^{}]*\}")
    original_tags = pattern.findall(original)
    translated_matches = list(pattern.finditer(translated))

    if not translated_matches:
        if original_tags:
            # Instead of reverting to original, append missing source tags
            # at the end of translated content to keep the translation.
            logger.warning(
                "Translated content dropped \\tag command(s); "
                "appending source tags to preserve target language output"
            )
            suffix = " " + " ".join(original_tags)
            return translated.rstrip() + suffix
        return translated

    if not original_tags:
        cleaned = pattern.sub("", translated)
        if cleaned != translated:
            logger.warning("Removed translated \\tag command(s) not present in source")
        return cleaned

    parts = []
    last = 0
    for i, m in enumerate(translated_matches):
        parts.append(translated[last:m.start()])
        if i < len(original_tags):
            parts.append(original_tags[i])
        else:
            # Drop extra translated tags beyond source count.
            logger.warning("Dropped extra translated \\tag command beyond source count")
        last = m.end()
    parts.append(translated[last:])
    restored = "".join(parts)

    if _has_tag_outside_display_math_context(restored) and not _has_tag_outside_display_math_context(original):
        # Keep the translated content instead of reverting to original.
        logger.warning(
            "Translated \\tag moved outside display math context; "
            "keeping translated content to preserve target language output"
        )

    return restored


def _parse_balanced_group(text: str, start: int, open_char: str, close_char: str) -> Tuple[bool, int]:
    """
    Parse a balanced bracket/brace group starting at `start`.

    Returns (ok, next_index_after_group).
    """
    if start >= len(text) or text[start] != open_char:
        return False, start

    depth = 0
    i = start
    while i < len(text):
        ch = text[i]
        if ch == open_char and not _is_escaped(text, i):
            depth += 1
        elif ch == close_char and not _is_escaped(text, i):
            depth -= 1
            if depth == 0:
                return True, i + 1
            if depth < 0:
                return False, i
        i += 1

    return False, i


def _skip_whitespace(text: str, index: int) -> int:
    """Skip whitespace from index and return the next non-space index."""
    n = len(text)
    while index < n and text[index].isspace():
        index += 1
    return index


def _has_well_formed_caption_commands(text: str) -> bool:
    """
    Validate `\\caption`, `\\subcaption`, and `\\captionof` command structure.

    - `\\caption` / `\\subcaption` expect optional `[...]` then mandatory `{...}`.
    - `\\captionof` expects `{type}` then optional `[...]` then mandatory `{...}`.
    """
    command_pattern = re.compile(r"\\(captionof|subcaption|caption)\b")

    for match in command_pattern.finditer(text):
        command = match.group(1)
        i = _skip_whitespace(text, match.end())

        if command == "captionof":
            ok, i = _parse_balanced_group(text, i, "{", "}")
            if not ok:
                return False
            i = _skip_whitespace(text, i)

        if i < len(text) and text[i] == "[":
            ok, i = _parse_balanced_group(text, i, "[", "]")
            if not ok:
                return False
            i = _skip_whitespace(text, i)

        ok, i = _parse_balanced_group(text, i, "{", "}")
        if not ok:
            return False

    return True


def restore_caption_command_structure(original: str, translated: str) -> str:
    """
    Restore caption command wrappers when translation breaks caption structure.

    We keep translated text whenever caption commands are structurally valid.
    If command count/order changes or command arguments become malformed, we
    fall back to source content for that caption unit.
    """
    if not original or not translated:
        return translated

    command_pattern = re.compile(r"\\(captionof|subcaption|caption)\b")
    original_commands = command_pattern.findall(original)
    if not original_commands:
        return translated

    translated_commands = command_pattern.findall(translated)
    if original_commands != translated_commands:
        logger.warning("Restored caption block due to command mismatch")
        return original

    if not _has_well_formed_caption_commands(translated):
        logger.warning("Restored caption block due to malformed caption command structure")
        return original

    return translated


def _has_well_formed_sectioning_commands(text: str) -> bool:
    """
    Validate sectioning command structure:
    \\section, \\subsection, \\subsubsection, \\paragraph, etc.

    Expected shape: optional `[...]` then required `{...}`.
    """
    section_pattern = re.compile(
        r"\\(?:part|chapter|section|subsection|subsubsection|paragraph|subparagraph)\*?\b"
    )

    for match in section_pattern.finditer(text):
        i = _skip_whitespace(text, match.end())

        if i < len(text) and text[i] == "[":
            ok, i = _parse_balanced_group(text, i, "[", "]")
            if not ok:
                return False
            i = _skip_whitespace(text, i)

        ok, i = _parse_balanced_group(text, i, "{", "}")
        if not ok:
            return False

    return True


def _extract_sectioning_commands(text: str) -> List[Dict[str, Any]]:
    """Extract sectioning commands with byte ranges and mandatory title argument."""
    section_pattern = re.compile(
        r"\\(?:part|chapter|section|subsection|subsubsection|paragraph|subparagraph)\*?\b"
    )

    commands = []
    for match in section_pattern.finditer(text):
        i = _skip_whitespace(text, match.end())

        if i < len(text) and text[i] == "[":
            ok, i = _parse_balanced_group(text, i, "[", "]")
            if not ok:
                return []
            i = _skip_whitespace(text, i)

        arg_start = i
        ok, arg_end = _parse_balanced_group(text, arg_start, "{", "}")
        if not ok:
            return []

        arg = text[arg_start:arg_end]
        commands.append(
            {
                "start": match.start(),
                "end": arg_end,
                "full": text[match.start():arg_end],
                "arg_start": arg_start,
                "arg_end": arg_end,
                "arg": arg,
                "arg_inner": arg[1:-1] if len(arg) >= 2 else "",
            }
        )

    return commands


def _repair_sectioning_command_math_preserve_translation(command_text: str) -> str:
    """Wrap likely math tokens inside a section title argument without losing translation."""
    commands = _extract_sectioning_commands(command_text)
    if not commands:
        return command_text

    cmd = commands[0]
    repaired_inner = _wrap_likely_math_tokens(cmd["arg_inner"])
    return (
        command_text[: cmd["arg_start"] + 1]
        + repaired_inner
        + command_text[cmd["arg_end"] - 1 :]
    )


def restore_sectioning_command_structure(original: str, translated: str) -> str:
    """
    Restore sectioning wrappers when translation breaks command arguments.
    """
    if not original or not translated:
        return translated

    section_pattern = re.compile(
        r"\\(?:part|chapter|section|subsection|subsubsection|paragraph|subparagraph)\*?\b"
    )
    original_commands = section_pattern.findall(original)
    if not original_commands:
        return translated

    translated_commands = section_pattern.findall(translated)
    if original_commands != translated_commands:
        logger.warning("Restored section block due to sectioning command mismatch")
        return original

    if not _has_well_formed_sectioning_commands(translated):
        logger.warning("Restored section block due to malformed sectioning command structure")
        return original

    original_entries = _extract_sectioning_commands(original)
    translated_entries = _extract_sectioning_commands(translated)
    if not original_entries or not translated_entries or len(original_entries) != len(translated_entries):
        logger.warning("Restored section block due to sectioning command parse mismatch")
        return original

    parts = []
    last = 0
    repaired_count = 0
    fallback_count = 0

    for idx, t_entry in enumerate(translated_entries):
        parts.append(translated[last:t_entry["start"]])

        replacement = t_entry["full"]
        o_entry = original_entries[idx]

        original_title_has_math = "$" in o_entry["arg_inner"]
        translated_title_has_math = "$" in t_entry["arg_inner"]
        translated_title_has_unsafe_math_tokens = bool(re.search(r"(?<!\\)[_^]", t_entry["arg_inner"]))

        if original_title_has_math and not translated_title_has_math and translated_title_has_unsafe_math_tokens:
            repaired = _repair_sectioning_command_math_preserve_translation(t_entry["full"])
            repaired_entries = _extract_sectioning_commands(repaired)
            repaired_arg_inner = repaired_entries[0]["arg_inner"] if repaired_entries else t_entry["arg_inner"]
            if _has_unsafe_math_tokens_outside_inline_math(repaired_arg_inner):
                replacement = o_entry["full"]
                fallback_count += 1
            else:
                replacement = repaired
                repaired_count += 1

        parts.append(replacement)
        last = t_entry["end"]

    parts.append(translated[last:])
    restored = "".join(parts)

    if repaired_count:
        logger.warning(f"Repaired {repaired_count} section title(s) by wrapping math tokens")
    if fallback_count:
        logger.warning(f"Restored {fallback_count} section title(s) from source due to unsafe math tokens")

    return restored


def restore_twopartpiecewise_commands(original: str, translated: str) -> str:
    """
    Restore `\\twopartpiecewise{...}{...}{...}{...}` calls from source by order.

    This command is structure-sensitive and frequently broken by LLM output
    (missing wrappers, stray `$`, or malformed braces), so we preserve the
    original command bodies to keep compilation stable.

    When translated content drops commands or has count mismatches, we keep
    the translated content (with warnings) instead of reverting to the
    original, to preserve target-language output.
    """
    if not original or not translated:
        return translated
    if r"\twopartpiecewise" not in original:
        return translated

    cmd_pattern = regex.compile(
        get_pattern_command_full("twopartpiecewise", n=4),
        flags=regex.DOTALL,
    )

    original_commands = [m.group(0) for m in cmd_pattern.finditer(original)]
    translated_matches = list(cmd_pattern.finditer(translated))

    if not original_commands:
        return translated
    if not translated_matches:
        # All commands dropped — append source commands at end instead of
        # reverting entire fragment to original.
        logger.warning(
            "Translated content dropped \\twopartpiecewise command(s); "
            "appending source commands to preserve target language output"
        )
        suffix = "\n" + "\n".join(original_commands)
        return translated.rstrip() + suffix
    if len(original_commands) != len(translated_matches):
        # Count mismatch — replace what we can, keep translated text.
        logger.warning(
            f"\\twopartpiecewise count mismatch (source={len(original_commands)}, "
            f"translated={len(translated_matches)}); replacing matched commands only"
        )

    # Replace matched translated commands with source commands (by order).
    parts = []
    last = 0
    for i, match in enumerate(translated_matches):
        parts.append(translated[last:match.start()])
        if i < len(original_commands):
            parts.append(original_commands[i])
        else:
            # Extra translated commands beyond source count — keep as-is.
            parts.append(match.group(0))
        last = match.end()
    parts.append(translated[last:])

    restored = "".join(parts)
    if restored != translated:
        logger.warning(f"Restored {min(len(original_commands), len(translated_matches))} \\twopartpiecewise command(s) from source")
    return restored


def _is_escaped(text: str, index: int) -> bool:
    """Return True when `text[index]` is escaped by an odd number of backslashes."""
    backslashes = 0
    i = index - 1
    while i >= 0 and text[i] == "\\":
        backslashes += 1
        i -= 1
    return (backslashes % 2) == 1


def _has_balanced_unescaped_braces(text: str) -> bool:
    """Check whether unescaped `{` and `}` are balanced and never underflow."""
    depth = 0
    for i, ch in enumerate(text):
        if ch == "{" and not _is_escaped(text, i):
            depth += 1
        elif ch == "}" and not _is_escaped(text, i):
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def _count_unclosed_unescaped_open_braces(text: str) -> int:
    """Count how many unescaped `{` remain unclosed by `}`."""
    depth = 0
    for i, ch in enumerate(text):
        if ch == "{" and not _is_escaped(text, i):
            depth += 1
        elif ch == "}" and not _is_escaped(text, i):
            if depth > 0:
                depth -= 1
    return depth


def restore_document_tail_structure(original: str, translated: str) -> str:
    """
    Restore a structurally complete document tail when translation is truncated.

    Typical symptoms:
    - missing `\\end{document}`
    - bibliography/contact tail cut off in the final lines
    """
    if not original or not translated:
        return translated

    end_doc_pattern = re.compile(r"\\end\s*\{document\}")
    if not end_doc_pattern.search(original):
        return translated
    if end_doc_pattern.search(translated):
        return translated

    anchor_patterns = [
        r"\\bibliographystyle\b",
        r"\\bibliography\b",
        r"\\begin\s*\{thebibliography\}",
        r"\\appendix\b",
    ]

    for pattern in anchor_patterns:
        src_matches = list(re.finditer(pattern, original))
        dst_matches = list(re.finditer(pattern, translated))
        if not src_matches or not dst_matches:
            continue

        src_idx = src_matches[-1].start()
        dst_idx = dst_matches[-1].start()
        restored = translated[:dst_idx] + original[src_idx:]
        if end_doc_pattern.search(restored):
            logger.warning("Restored document tail from source due to missing \\end{document}")
            return restored

    restored = translated.rstrip()
    missing_braces = _count_unclosed_unescaped_open_braces(restored)
    if missing_braces > 0:
        restored += "\n" + ("}" * missing_braces)
    restored += "\n\\end{document}\n"
    logger.warning("Appended fallback \\end{document} to recover truncated output tail")
    return restored


def restore_math_environment_blocks(original: str, translated: str) -> str:
    """
    Restore damaged math environments from source by occurrence order.

    Only targeted environments are considered (`align`, `equation`, `gather`,
    `multline`, `eqnarray`, `alignat`, `flalign`, with optional `*`).
    A translated math block is replaced by source only when brace structure is
    syntactically unsafe (unbalanced/underflow).
    """
    if not original or not translated:
        return translated

    env_pattern = re.compile(
        r"\\begin\{(alignat\*?|align\*?|flalign\*?|gather\*?|multline\*?|equation\*?|eqnarray\*?)\}.*?\\end\{\1\}",
        flags=re.DOTALL,
    )
    original_blocks = list(env_pattern.finditer(original))
    translated_blocks = list(env_pattern.finditer(translated))
    if not original_blocks or not translated_blocks:
        return translated

    parts = []
    last = 0
    replaced_count = 0
    for idx, match in enumerate(translated_blocks):
        parts.append(translated[last:match.start()])
        block = match.group(0)

        if (not _has_balanced_unescaped_braces(block)) and idx < len(original_blocks):
            parts.append(original_blocks[idx].group(0))
            replaced_count += 1
        else:
            parts.append(block)
        last = match.end()

    parts.append(translated[last:])
    if replaced_count:
        logger.warning(f"Restored {replaced_count} damaged math environment block(s) from source")
    return "".join(parts)


def restore_inline_math_segments(original: str, translated: str) -> str:
    """
    Restore malformed inline `$...$` math segments from source by occurrence order.

    Only segments with structurally unsafe brace balance are replaced, so normal
    translated prose remains intact.
    """
    if not original or not translated:
        return translated

    inline_pattern = re.compile(
        r"(?<!\\)(?<!\$)\$(?!\$).*?(?<!\\)(?<!\$)\$(?!\$)",
        flags=re.DOTALL,
    )
    original_segments = inline_pattern.findall(original)
    translated_segments = list(inline_pattern.finditer(translated))
    if not original_segments or not translated_segments:
        return translated

    parts = []
    last = 0
    replaced_count = 0
    for idx, match in enumerate(translated_segments):
        parts.append(translated[last:match.start()])
        segment = match.group(0)
        inner = segment[1:-1] if len(segment) >= 2 else segment

        if (not _has_balanced_unescaped_braces(inner)) and idx < len(original_segments):
            parts.append(original_segments[idx])
            replaced_count += 1
        else:
            parts.append(segment)
        last = match.end()

    parts.append(translated[last:])
    if replaced_count:
        logger.warning(f"Restored {replaced_count} malformed inline math segment(s) from source")
    return "".join(parts)


def _has_unsafe_math_tokens_outside_inline_math(text: str) -> bool:
    """Detect `_`/`^` tokens outside inline `$...$` regions."""
    sanitized = re.sub(r"(?<!\\)(?<!\$)\$.*?(?<!\\)(?<!\$)\$", "", text)
    return bool(re.search(r"(?<!\\)[_^]", sanitized))


def _wrap_likely_math_tokens(header_text: str) -> str:
    """
    Wrap common math-like tokens (e.g., Y_i, x^2) in `$...$` within header text.
    """
    if not header_text:
        return header_text

    # Simple variable/subscript/superscript token patterns.
    token_pattern = re.compile(
        r"(?<!\\)(?:[A-Za-z]+(?:_[A-Za-z0-9]+)+(?:\^[A-Za-z0-9]+)*|[A-Za-z]+(?:\^[A-Za-z0-9]+)+)"
    )

    def _replacer(match: re.Match) -> str:
        token = match.group(0)
        return f"${token}$"

    return token_pattern.sub(_replacer, header_text)


def _repair_begin_header_math_preserve_translation(begin_cmd: str) -> str:
    """
    Try to preserve translated begin-header text while repairing unsafe math tokens.
    """
    m = re.match(r"(\\begin\s*\{[^}]+\}\s*\[)([^\]]*)(\])", begin_cmd, flags=re.DOTALL)
    if not m:
        return begin_cmd

    prefix, header_text, suffix = m.groups()
    repaired_header = _wrap_likely_math_tokens(header_text)
    return f"{prefix}{repaired_header}{suffix}"


def _strip_unsafe_inner_environment_wrapper(body: str, outer_env: str) -> str:
    """
    Remove a full-body translated inner environment wrapper when its env name is unsafe.

    Example:
      outer: \\begin{definition} ... \\end{definition}
      body : \\begin{定义} ... \\end{定义}
    """
    if not body:
        return body

    stripped = body.strip()
    begin_inner_match = re.match(
        r"\s*\\begin\s*\{(?P<env>[^}]+)\}(?:\s*\[[^\]]*\])?",
        stripped,
        flags=re.DOTALL,
    )
    if not begin_inner_match:
        return stripped

    inner_env = begin_inner_match.group("env")
    if inner_env == outer_env:
        return stripped

    # Keep valid ASCII LaTeX env names unchanged; only strip clearly unsafe names.
    if re.match(r"^[A-Za-z*@]+$", inner_env):
        return stripped

    end_inner_match = re.search(
        rf"(\\end\s*\{{{re.escape(inner_env)}\}})\s*$",
        stripped,
        flags=re.DOTALL,
    )
    if not end_inner_match:
        return stripped

    inner_body = stripped[begin_inner_match.end():end_inner_match.start()].strip()
    return inner_body or stripped


def restore_environment_structure(original: str, translated: str) -> str:
    """
    Restore critical environment wrappers when translation drops or corrupts them.

    Scope:
    - Only applies when `original` is a single LaTeX environment block.
    - Ensures `\\begin{env}` / `\\end{env}` pair exists in translated content.
    - If translated begin header loses math delimiters from source and introduces
      unsafe `_`/`^` tokens, fallback to the original begin header.
    """
    if not original or not translated:
        return translated

    begin_original_match = re.match(
        r"\s*(\\begin\s*\{(?P<env>[^}]+)\}(?:\s*\[[^\]]*\])?)",
        original,
        flags=re.DOTALL,
    )
    if not begin_original_match:
        return translated

    env_name = begin_original_match.group("env")
    original_begin_cmd = begin_original_match.group(1)

    end_original_match = re.search(
        rf"(\\end\s*\{{{re.escape(env_name)}\}})\s*$",
        original,
        flags=re.DOTALL,
    )
    if not end_original_match:
        return translated
    original_end_cmd = end_original_match.group(1)

    begin_translated_match = re.match(
        rf"\s*(\\begin\s*\{{{re.escape(env_name)}\}}(?:\s*\[[^\]]*\])?)",
        translated,
        flags=re.DOTALL,
    )
    end_translated_match = re.search(
        rf"(\\end\s*\{{{re.escape(env_name)}\}})\s*$",
        translated,
        flags=re.DOTALL,
    )

    missing_begin = begin_translated_match is None
    missing_end = end_translated_match is None

    translated_begin_cmd = begin_translated_match.group(1) if begin_translated_match else original_begin_cmd
    original_begin_has_math = "$" in original_begin_cmd
    translated_begin_has_math = "$" in translated_begin_cmd
    translated_begin_has_unsafe_math_tokens = bool(re.search(r"(?<!\\)[_^]", translated_begin_cmd))

    begin_header_needs_repair = (
        original_begin_has_math
        and not translated_begin_has_math
        and translated_begin_has_unsafe_math_tokens
    )

    if not missing_begin and not missing_end:
        translated_body = translated[begin_translated_match.end():end_translated_match.start()].strip()
        normalized_body = _strip_unsafe_inner_environment_wrapper(translated_body, env_name)
        if not begin_header_needs_repair and normalized_body == translated_body:
            return translated

    begin_cmd = translated_begin_cmd
    if begin_header_needs_repair:
        repaired_begin_cmd = _repair_begin_header_math_preserve_translation(translated_begin_cmd)
        if _has_unsafe_math_tokens_outside_inline_math(repaired_begin_cmd):
            # Final fallback to source header if translated header still unsafe.
            begin_cmd = original_begin_cmd
        else:
            begin_cmd = repaired_begin_cmd

    body = translated
    if begin_translated_match:
        body = body[begin_translated_match.end():]
    end_in_body = re.search(
        rf"(\\end\s*\{{{re.escape(env_name)}\}})\s*$",
        body,
        flags=re.DOTALL,
    )
    if end_in_body:
        body = body[:end_in_body.start()]

    body = body.strip()
    body = _strip_unsafe_inner_environment_wrapper(body, env_name)
    if not body:
        original_body = original[begin_original_match.end():end_original_match.start()]
        body = original_body.strip()

    return f"{begin_cmd}\n{body}\n{original_end_cmd}"


def extract_pure_text(dir):
    """Extract pure text from LaTeX project"""
    main_file_path = find_main_tex_file(dir)
    if main_file_path is None:
        raise FileNotFoundError(f"Main TeX file not found in {dir}")
    full_latex_code = merge_tex_from_inputs(main_file_path)
    main_latex_code = process_latex_to_eva(full_latex_code)
    pure_text = extract_text_from_tex(main_latex_code)
    return pure_text


def get_texts_from_data(folder_path, output_folder):
    """Extract text from all projects in a folder"""
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    extract_compressed_files(folder_path)
    projects = get_profect_dirs(folder_path)
    
    for project in tqdm(projects, desc="Processing projects", unit="project"):
        try:
            text = extract_pure_text(project)
            project_name = os.path.basename(project)
            output_file = os.path.join(output_folder, f"{project_name}.txt")
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(text)
        except Exception as e:
            logger.error(f"Error processing project {project}: {e}")
            continue


def extract_pure_tags(dir):
    """Extract tag structure from LaTeX project"""
    main_file_path = find_main_tex_file(dir)
    if main_file_path is None:
        raise FileNotFoundError(f"Main TeX file not found in {dir}")
    main_latex_code = merge_tex_from_inputs(main_file_path)
    nodes = extract_latex_nodes(main_latex_code)
    tag_structure = extract_structure(nodes)
    return tag_structure


def loop_files(dir):
    """Recursively list all files in a directory"""
    all_files = []
    for root, dirs, files in os.walk(dir):
        for file in files:
            all_files.append(os.path.join(root, file))
    return all_files


def read_tex_file(path):
    """Read LaTeX file"""
    with open(path, 'r', encoding='utf-8') as f:
        latex_code = f.read()
    return latex_code


def read_json_file(path):
    """Read JSON file"""
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data


def find_tex_files(dir):
    """Find all .tex files in a directory"""
    all_files = loop_files(dir)
    tex_files = [f for f in all_files if f.endswith('.tex')]
    return tex_files


def remove_comments(tex: str) -> str:
    """
    Remove both % line comments and \\begin{comment} ... \\end{comment} blocks from LaTeX code.
    """
    # Remove \begin{comment}...\end{comment} environments
    tex = re.sub(r'\\begin\s*\{comment\}.*?\\end\s*\{comment\}', '', tex, flags=re.DOTALL)

    lines = tex.splitlines()
    cleaned = []
    for line in lines:
        stripped_line = line.lstrip()
        # Skip full-line comments (ignoring leading whitespace)
        if re.match(r'^(?<!\\)%', stripped_line):
            continue
        # Remove inline comments (ignore escaped %)
        line = re.sub(r'(?<!\\)%.*', '', line)
        cleaned.append(line.rstrip())

    return '\n'.join(cleaned)


def compress_newlines(tex):
    """
    Replace consecutive newlines (including spaces) exceeding four with exactly two newlines.
    """
    return re.sub(r'(\s*\n\s*){3,}', '\n\n', tex)


def get_env_pattern(command_name):
    """Get the regex pattern for matching environments"""
    get_command_env = lambda name: rf"\\begin{spaces}\{{(?!document\b|center\b|proof\b|multicols\b)({name})\}}{spaces}({options})?(.*?)\\end{spaces}\{{\1\}}"
    command_env = get_command_env(command_name)
    env_pattern = regex.compile(command_env, regex.DOTALL)
    return env_pattern


def get_abstract_pattern():
    """Get the regex pattern for matching \\begin{abstract} and \\end{abstract} commands"""
    command_name = r'abstract'
    get_command_env = lambda name: rf"\\begin{spaces}\{{({name})\}}{spaces}({options})?(.*?)\\end{spaces}\{{\1\}}"
    command_abstract = get_command_env(command_name)
    abstract_pattern = regex.compile(command_abstract, regex.DOTALL)
    return abstract_pattern


def get_keywords_pattern():
    """Get the regex pattern for matching \\keywords commands"""
    command_name = r'keywords'
    command = get_pattern_command_full(command_name)
    keywords_pattern = regex.compile(command, regex.DOTALL)
    return keywords_pattern


def get_section_pattern():
    """Get the regex pattern for matching section commands"""
    command_name = r'section|subsection|subsubsection'
    command = get_pattern_command_full(command_name)
    section_pattern = regex.compile(command, regex.DOTALL)
    return section_pattern


def get_begin_document_pattern():
    """Get the regex pattern for matching \\begin{document} command"""
    pattern = regex.compile(r'\\begin\s*\{\s*document\s*\}', regex.DOTALL)
    return pattern


def get_newcommand_pattern():
    """Get the regex pattern for matching \\newcommand commands"""
    cmd_types = r'newcommand\*?|def|renewcommand'
    env_types = r'newenvironment|renewenvironment'
    spaces_nl = r'\s*'
    
    # We must separate newcommand (1 argument block) and newenvironment (2 argument blocks)
    # The get_pattern_brace(n) expects 'n' to be the regex group ID of its own outer capture group
    newcommand = (
        rf'\\(?:'
        rf'(?:(?:{cmd_types}){spaces_nl}(?:\{{\\([a-zA-Z]+)\}}|\\([a-zA-Z]+)){spaces_nl}(?:\[(\d)\])?{spaces_nl}({get_pattern_brace(4)}))'
        rf'|'
        rf'(?:(?:{env_types}){spaces_nl}\{{([a-zA-Z*]+)\}}{spaces_nl}(?:\[(\d)\])?{spaces_nl}({get_pattern_brace(8)}){spaces_nl}({get_pattern_brace(10)}))'
        rf')'
    )
    newcommand_pattern = regex.compile(newcommand, regex.DOTALL)
    return newcommand_pattern


def get_command_pattern(name):
    """Get the regex pattern for matching LaTeX commands"""
    command = get_pattern_command_full(name)
    command_pattern = regex.compile(command, regex.DOTALL)
    return command_pattern


def get_captionof_pattern():
    """Match \\captionof{env}{text} structure using regex with support for nested braces"""
    pattern = regex.compile(r"""
        \\captionof          # match \captionof
        \s*                  # optional whitespace
        (?P<braces>          # named group 'braces' to handle nested {}
            \{               # opening {
                (?:          # non-capturing group
                    [^{}]+   # non-brace characters
                    |        # OR
                    (?&braces)  # recursive match for nested braces
                )*
            \}               # closing }
        )
        \s*                  # optional whitespace
        (?P=braces)          # repeat the same structure for the second argument
    """, regex.VERBOSE | regex.DOTALL)
    return pattern


def _detect_ctex_conflicts(preamble: str) -> List[str]:
    """
    Detect command names that conflict with ctex/CJK package definitions.

    ctex and CJK packages redefine certain short commands like \\I and \\O.
    If the document also defines these commands, a 'Command already defined'
    error occurs at compilation.

    Args:
        preamble: The LaTeX preamble text (before \\begin{document}).

    Returns:
        List of conflicting command names (without backslash), e.g. ['I', 'O'].
    """
    # Commands known to be redefined by ctex/CJK
    CTEX_RESERVED = {'I', 'O', 'TeX', 'LaTeX', 'ij', 'IJ'}

    # Match \\newcommand{\\X}, \\def\\X, \\renewcommand{\\X},
    # \\DeclareRobustCommand{\\X}, \\let\\X = ...
    define_re = re.compile(
        r'\\(?:newcommand\*?|renewcommand\*?|def|DeclareRobustCommand\*?|let)'
        r'\s*\{?\\([A-Za-z]+)\}?'
    )
    conflicts = []
    for m in define_re.finditer(preamble):
        cmd = m.group(1)
        if cmd in CTEX_RESERVED:
            conflicts.append(cmd)
    # Deduplicate while preserving order
    seen = set()
    return [c for c in conflicts if not (c in seen or seen.add(c))]


def add_ctex_package(latex_code, tex_file_path: str = None):
    """Add ctex package for Chinese support and handle XeLaTeX compatibility.

    Args:
        latex_code: The main .tex source code.
        tex_file_path: Optional path to the .tex file.  When provided, also
            scans sibling .cls / .sty files and neutralises pdfLaTeX-only
            font packages (fontenc[T1], newtxtext, …) that would otherwise
            prevent CJK characters from rendering under xelatex+ctex.
    """
    if "\\usepackage[UTF8]{ctex}" not in latex_code:
        ctex_package = "\\usepackage[UTF8]{ctex}"
        documentclass = r'documentclass'
        documentclass_pattern = get_command_pattern(documentclass)
        match = documentclass_pattern.search(latex_code)
        if match:
            position = match.end()

            # Task 4: Detect ctex command conflicts and inject \let\<cmd>\relax
            # to neutralise author-defined commands before ctex redefines them.
            preamble = latex_code[:position]
            conflicts = _detect_ctex_conflicts(preamble)
            conflict_prefix = ""
            if conflicts:
                relax_lines = "\n".join(
                    f"\\let\\{cmd}\\relax  % ctex conflict resolution"
                    for cmd in conflicts
                )
                conflict_prefix = "\n" + relax_lines
                logger.warning(
                    "[ctex compat] Detected conflicting command(s) %s; "
                    "injecting \\let\\<cmd>\\relax before \\usepackage{ctex}",
                    conflicts,
                )

            latex_code = (
                latex_code[:position]
                + conflict_prefix
                + "\n" + ctex_package + "\n"
                + latex_code[position:]
            )

    # Comment out pdfLaTeX-specific commands in the main .tex
    latex_code = _comment_out_pdflatex_commands(latex_code)

    # Also patch sibling .cls / .sty files that may load pdfLaTeX-only font
    # packages internally (e.g. atlasdoc.cls loading fontenc[T1] + newtxtext).
    if tex_file_path:
        _patch_sibling_style_files(tex_file_path)

    # XeCJK/ctex may leave math families (notably 6/11) without script fonts
    # in some amsart-class documents, causing `scriptfont ... undefined` errors.
    latex_code = _inject_cjk_math_family_fallback(latex_code)

    # Render stray \begin{CJK} harmless under xeCJK
    latex_code = _inject_cjk_dummy_environments(latex_code)

    return latex_code


def _inject_cjk_math_family_fallback(latex_code: str) -> str:
    """Inject a defensive math-family fallback block for CJK engine paths."""
    marker = "% CJK math family fallback"
    if marker in latex_code:
        return latex_code

    fallback_block = (
        f"{marker}\n"
        "\\AtBeginDocument{\n"
        "  \\textfont6=\\textfont2\n"
        "  \\scriptfont6=\\scriptfont2\n"
        "  \\scriptscriptfont6=\\scriptscriptfont2\n"
        "  \\textfont11=\\textfont2\n"
        "  \\scriptfont11=\\scriptfont2\n"
        "  \\scriptscriptfont11=\\scriptscriptfont2\n"
        "}"
    )

    # Prefer injecting directly after ctex/xeCJK package lines.
    for pkg_pattern in [
        r'\\usepackage(?:\[[^\]]*\])?\{ctex\}',
        r'\\usepackage(?:\[[^\]]*\])?\{xeCJK\}',
    ]:
        match = re.search(pkg_pattern, latex_code)
        if match:
            pos = match.end()
            return latex_code[:pos] + "\n" + fallback_block + "\n" + latex_code[pos:]

    return _inject_after_documentclass(latex_code, fallback_block)


def _inject_cjk_dummy_environments(latex_code: str) -> str:
    """Inject robust dummy CJK environments for translated documents.
    
    Some authors use \\usepackage{CJKutf8} and \\begin{CJK}{UTF8}{gbsn} ... \\end{CJK}
    to insert CJK characters in an English original. Since the translation uses
    ctex and runs under xelatex, the CJK environment is undefined and crashes compilation.
    This injects empty environment definitions to prevent these crashes.
    """
    marker = "% Dummy CJK environments for ctex/xeCJK compatibility"
    if marker in latex_code:
        return latex_code

    dummy_block = (
        f"{marker}\n"
        "\\makeatletter\n"
        "\\@ifundefined{CJK}{\n"
        "  \\newenvironment{CJK}[2]{}{}\n"
        "  \\newenvironment{CJK*}[2]{}{}\n"
        "}{}\n"
        "\\makeatother"
    )

    # Prefer injecting directly after ctex/xeCJK package lines.
    for pkg_pattern in [
        r'\\usepackage(?:\[[^\]]*\])?\{ctex\}',
        r'\\usepackage(?:\[[^\]]*\])?\{xeCJK\}',
    ]:
        match = re.search(pkg_pattern, latex_code)
        if match:
            pos = match.end()
            return latex_code[:pos] + "\n" + dummy_block + "\n" + latex_code[pos:]

    return _inject_after_documentclass(latex_code, dummy_block)


def _comment_out_pdflatex_commands(latex_code: str) -> str:
    """
    Comment out pdfLaTeX-specific commands that are incompatible with XeLaTeX.
    
    This addresses the issue where commands like \\pdfoutput=1 or \\pdfinfo{...}
    cause compilation errors when using XeLaTeX (needed for CJK support),
    resulting in blank first pages.
    
    Handles both single-line commands and multi-line block commands like \\pdfinfo{...}.
    
    Args:
        latex_code: The LaTeX source code
        
    Returns:
        Modified LaTeX code with pdfLaTeX-specific commands commented out
    """
    import re
    
    # --- Step 1: Handle multi-line block commands (e.g. \pdfinfo{ ... }) ---
    # These span multiple lines and need to be handled before line-by-line processing.
    block_command_patterns = [
        r'\\pdfinfo\s*\{',           # \pdfinfo{...}
        r'\\pdfcatalog\s*\{',        # \pdfcatalog{...}
        r'\\pdftrailer\s*\{',        # \pdftrailer{...}
    ]
    
    for block_pattern in block_command_patterns:
        start_re = re.compile(block_pattern)
        result = start_re.search(latex_code)
        while result:
            start = result.start()
            # Find the matching closing brace by counting brace depth
            depth = 0
            end = result.start()
            for i in range(result.start(), len(latex_code)):
                if latex_code[i] == '{':
                    depth += 1
                elif latex_code[i] == '}':
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            
            if end > result.start():
                block_content = latex_code[start:end]
                # Comment out each line of the block
                commented_lines = []
                for line in block_content.splitlines():
                    if line.lstrip().startswith('%'):
                        commented_lines.append(line)
                    else:
                        commented_lines.append(f'% {line}  % Commented for XeLaTeX compatibility' if line.strip() else line)
                commented_block = '\n'.join(commented_lines)
                latex_code = latex_code[:start] + commented_block + latex_code[end:]
                logger.debug(f"Commented out pdfLaTeX block command: {block_content[:50].strip()}...")
                # Search again from after the replaced block
                result = start_re.search(latex_code, start + len(commented_block))
            else:
                break
    
    # --- Step 2: Handle single-line pdfLaTeX-specific commands ---
    lines = latex_code.splitlines()
    modified_lines = []
    
    # Single-line commands that need to be commented out for XeLaTeX compatibility
    pdflatex_single_patterns = [
        r'\\pdfoutput\s*=\s*\d+',          # \pdfoutput=1
        r'\\pdfcompresslevel\s*=\s*\d+',   # \pdfcompresslevel=9
        r'\\pdfobjcompresslevel\s*=\s*\d+', # \pdfobjcompresslevel=2
        r'\\pdfminorversion\s*=\s*\d+',    # \pdfminorversion=7
        r'\\pdfpagewidth\s*=',             # \pdfpagewidth=...
        r'\\pdfpageheight\s*=',            # \pdfpageheight=...
        # Font packages incompatible with xelatex + ctex/xeCJK
        r'(?:\\usepackage|\\RequirePackage)\s*\[T1\]\s*\{fontenc\}',  # fontenc[T1]
        r'(?:\\usepackage|\\RequirePackage)\s*(?:\[[^\]]*\])?\s*\{newtxtext\}',
        r'(?:\\usepackage|\\RequirePackage)\s*(?:\[[^\]]*\])?\s*\{newtxmath\}',
        r'(?:\\usepackage|\\RequirePackage)\s*(?:\[[^\]]*\])?\s*\{txfonts\}',
        r'\\pdfinclusioncopyfonts\s*=\s*\d+',  # \pdfinclusioncopyfonts=1
    ]
    
    combined_pattern = re.compile('|'.join(pdflatex_single_patterns))
    
    for line in lines:
        stripped = line.lstrip()
        # Skip already commented lines
        if stripped.startswith('%'):
            modified_lines.append(line)
            continue
            
        # Check if line matches any pdfLaTeX-specific single-line pattern
        if combined_pattern.search(line):
            # Comment out the line with explanation
            modified_lines.append(f'% {line.lstrip()}  % Commented for XeLaTeX compatibility')
            logger.debug(f"Commented out pdfLaTeX command: {line.strip()}")
        else:
            modified_lines.append(line)
    
    return '\n'.join(modified_lines)


def _patch_sibling_style_files(tex_file_path: str) -> None:
    """Patch .cls and .sty files in the same directory as the .tex file.

    Custom document classes (e.g. ``atlasdoc.cls``) often load pdfLaTeX-only
    font packages such as ``fontenc[T1]``, ``newtxtext``, or ``newtxmath``
    via ``\\RequirePackage``.  Under xelatex + ctex, these packages override
    the Unicode font handling and make CJK characters invisible (rendered
    with ``nullfont``).

    This function scans sibling ``.cls`` and ``.sty`` files and applies the
    same ``_comment_out_pdflatex_commands`` transformation used on the main
    ``.tex`` file.
    """
    import glob

    tex_dir = os.path.dirname(os.path.abspath(tex_file_path))
    patched = 0

    for ext in ("*.cls", "*.sty"):
        for style_path in glob.glob(os.path.join(tex_dir, ext)):
            try:
                with open(style_path, "r", encoding="utf-8", errors="replace") as f:
                    original = f.read()

                patched_content = _comment_out_pdflatex_commands(original)

                if patched_content != original:
                    with open(style_path, "w", encoding="utf-8") as f:
                        f.write(patched_content)
                    patched += 1
                    logger.info(
                        f"[CJK compat] Patched pdfLaTeX font packages in "
                        f"{os.path.basename(style_path)}"
                    )
            except Exception as e:
                logger.warning(
                    f"[CJK compat] Failed to patch {style_path}: {e}"
                )

    if patched:
        logger.info(f"[CJK compat] Patched {patched} style file(s) for xelatex+ctex")



def add_cyrillic_font_support(latex_code: str, target_language: str = "ru") -> str:
    """
    Add Cyrillic font support for languages like Russian, Ukrainian, Bulgarian, etc.
    Requires XeLaTeX (the compiler will fallback to xelatex after pdflatex fails).

    Strategy:
    1. Comment out pdfLaTeX-only encoding packages (T1, T2A fontenc; utf8 inputenc; times; lmodern)
       that conflict with XeLaTeX's fontspec approach.
    2. Inject fontspec + CMU Serif (Computer Modern Unicode), which is bundled with
       TeX Live / MiKTeX and natively supports Cyrillic characters.
    """
    # Step 1: Comment out packages incompatible with XeLaTeX Cyrillic rendering
    packages_to_comment = [
        r'\usepackage[T1]{fontenc}',
        r'\usepackage[T2A]{fontenc}',
        r'\usepackage[utf8]{inputenc}',
        r'\usepackage[utf8x]{inputenc}',
        r'\usepackage{times}',
        r'\usepackage{mathptmx}',
        r'\usepackage{lmodern}',
    ]

    lines = latex_code.splitlines()
    modified_lines = []
    for line in lines:
        stripped = line.strip()
        commented = False
        if not stripped.startswith('%'):
            for pkg in packages_to_comment:
                if stripped.startswith(pkg):
                    modified_lines.append(
                        f'% {line.lstrip()}  % Commented for XeLaTeX Cyrillic compatibility'
                    )
                    logger.debug(f"Commented out for Cyrillic support: {line.strip()}")
                    commented = True
                    break
        if not commented:
            modified_lines.append(line)
    latex_code = '\n'.join(modified_lines)

    # Step 2: Comment out pdfLaTeX primitive commands (\pdfoutput, \pdfinfo, etc.)
    latex_code = _comment_out_pdflatex_commands(latex_code)

    # Step 3: Inject fontspec + CMU Serif after \documentclass
    # CMU Serif (Computer Modern Unicode) is bundled with TeX Live / MiKTeX
    # and fully supports Cyrillic characters out of the box.
    cyrillic_font_block = (
        "\n\\usepackage{fontspec}\n"
        "\\setmainfont{CMU Serif}"
        "[BoldFont={CMU Serif Bold},"
        "ItalicFont={CMU Serif Italic},"
        "BoldItalicFont={CMU Serif Bold Italic}]\n"
        "\\setsansfont{CMU Sans Serif}\n"
        "\\setmonofont{CMU Typewriter Text}\n"
    )

    if "\\usepackage{fontspec}" not in latex_code:
        documentclass_pattern = get_command_pattern(r'documentclass')
        match = documentclass_pattern.search(latex_code)
        if match:
            position = match.end()
            latex_code = latex_code[:position] + cyrillic_font_block + latex_code[position:]
            logger.info(
                f"Injected fontspec + CMU Serif for Cyrillic support (language={target_language})"
            )
        else:
            logger.warning("Could not find \\documentclass to inject Cyrillic font support")
    else:
        logger.info(f"fontspec already present, skipping Cyrillic font injection for: {target_language}")

    return latex_code


def _fix_page_overflow_for_cjk(latex_code: str) -> str:
    """Fix page overflow issues that occur when CJK fonts are used with
    document classes / packages that assume Western line heights.

    CJK characters have taller line heights than Latin glyphs.  When a document
    uses packages like ``a4wide`` (which aggressively expand ``\\textheight`` to
    fill A4 pages under Western metrics), the extra CJK line height causes
    content to overflow past the physical PDF page boundary.  The ``xdvipdfmx``
    driver then clips the overflowing content, resulting in text being visually
    cut in half at the bottom of each page.

    This function applies two mitigations:

    1. **Replace ``a4wide``** with ``geometry[a4paper, margin=2cm]`` so that
       ``\\textheight`` is properly recalculated for the actual (larger) line
       height.  The ``geometry`` package also ensures the PDF MediaBox is set
       to A4, preventing canvas-size mismatches.

    2. **Inject ``\\raggedbottom``** to prevent the ``\\flushbottom`` default
       (used by ``amsart`` and many journal classes) from stretching vertical
       glue, which can push the last line of a page below the bottom margin.
    """
    # --- 1. Replace a4wide with geometry[a4paper] --------------------------
    # a4wide sets aggressive text dimensions that overflow with CJK line height.
    # It can appear as standalone (\usepackage{a4wide}) or inside a combo
    # (\usepackage{bbm, a4wide}).

    # Pattern A: standalone  \usepackage{a4wide}  or  \usepackage[...]{a4wide}
    standalone_pat = re.compile(
        r'\\usepackage\s*(?:\[[^\]]*\])?\s*\{a4wide\}'
    )
    # Pattern B: combo like  \usepackage{bbm, a4wide}  or  \usepackage{a4wide, bbm}
    #   We detect any \usepackage{...} whose brace content mentions a4wide
    combo_pat = re.compile(
        r'(\\usepackage\s*(?:\[[^\]]*\])?\s*\{)([^}]*\ba4wide\b[^}]*)(\})'
    )

    combo_m = combo_pat.search(latex_code)
    standalone_m = standalone_pat.search(latex_code)

    a4wide_removed = False

    if combo_m:
        pkg_list = combo_m.group(2)
        # Split packages, remove a4wide, keep the rest
        pkgs = [p.strip() for p in pkg_list.split(',') if p.strip().lower() != 'a4wide']
        if pkgs:
            # There are other packages remaining — keep them, remove a4wide
            new_line = combo_m.group(1) + ', '.join(pkgs) + combo_m.group(3)
        else:
            # a4wide was the only package — comment out the entire line
            new_line = '% ' + combo_m.group(0) + '  % Removed for CJK compat'
        latex_code = latex_code[:combo_m.start()] + new_line + latex_code[combo_m.end():]
        a4wide_removed = True
    elif standalone_m:
        # Comment out standalone a4wide line
        latex_code = (
            latex_code[:standalone_m.start()]
            + '% ' + standalone_m.group(0) + '  % Removed for CJK compat'
            + latex_code[standalone_m.end():]
        )
        a4wide_removed = True

    if a4wide_removed:
        # Inject geometry[a4paper] if not already present
        has_geometry = re.search(
            r'\\usepackage\s*(?:\[[^\]]*\])?\s*\{geometry\}', latex_code
        )
        if not has_geometry:
            geometry_line = (
                '\\usepackage[a4paper, left=2cm, right=2cm, '
                'top=2.5cm, bottom=2.5cm]{geometry}'
            )
            latex_code = _inject_after_documentclass(latex_code, geometry_line)
        else:
            # geometry exists — make sure it has a4paper
            geo_m = re.search(
                r'(\\usepackage\s*\[)([^\]]*)(\]\s*\{geometry\})', latex_code
            )
            if geo_m and 'a4paper' not in geo_m.group(2):
                latex_code = (
                    latex_code[:geo_m.start()]
                    + geo_m.group(1) + 'a4paper, ' + geo_m.group(2) + geo_m.group(3)
                    + latex_code[geo_m.end():]
                )
        logger.info("Replaced a4wide with geometry[a4paper] for CJK page-overflow fix")

    # --- 2. Inject \raggedbottom -------------------------------------------
    if '\\raggedbottom' not in latex_code:
        begin_doc = re.search(r'\\begin\s*\{document\}', latex_code)
        if begin_doc:
            pos = begin_doc.start()
            latex_code = latex_code[:pos] + '\\raggedbottom\n' + latex_code[pos:]
        else:
            latex_code = _inject_after_documentclass(latex_code, '\\raggedbottom')
        logger.info("Injected \\raggedbottom for CJK page-overflow fix")

    return latex_code


def add_cjk_package(latex_code: str, target_language: str = "en", tex_file_path: str = None) -> str:
    """
    Dynamically inject the appropriate font/language package based on target language.

    Language categories and their handling:
    - Chinese (zh/ch): inject ctex with UTF8, comment out pdfLaTeX-specific commands.
    - Japanese (ja): inject luatexja (strictly enforcing LuaLaTeX compatibility).
    - Korean (ko): inject kotex (multi-engine safe).
    - Russian (ru) / Cyrillic: inject fontspec + CMU Serif, comment out conflicting encodings.
    - Latin-extended / English (en, de, fr, es, pt, it, nl, pl, ...):
        Zero-touch pass-through. Preserves native pdflatex packages (T1, inputenc) unharmed.
    """
    
    # Globally strip \pdfoutput=1 which is obsolete and breaks LuaTeX (prints "=1" on a blank page).
    # Since we use latexmk to force PDF output, this primitive is never strictly required.
    latex_code = re.sub(r'\\pdfoutput\s*=\s*\d+', r'% \\pdfoutput stripped', latex_code)
    
    lang = target_language.lower()
    if lang in ("zh", "ch"):
        # Chinese: use ctex package
        latex_code = add_ctex_package(latex_code, tex_file_path=tex_file_path)
        return _fix_page_overflow_for_cjk(latex_code)
    elif lang == "ko":
        # Korean: use kotex package for reliable cross-platform compilation
        if "\\usepackage{kotex}" not in latex_code:
            ko_full_block = "\n\\usepackage{kotex}\n"
            documentclass_pattern = get_command_pattern(r'documentclass')
            match = documentclass_pattern.search(latex_code)
            if match:
                position = match.end()
                latex_code = latex_code[:position] + ko_full_block + latex_code[position:]
                logger.info("Injected kotex for Korean compilation")
        return _fix_page_overflow_for_cjk(latex_code)
    elif lang == "ja":
        # Japanese: solely use luatexja to natively enforce LuaLaTeX safety without font guesses
        if "\\usepackage{luatexja}" not in latex_code:
            ja_full_block = "\n\\usepackage{luatexja}\n"
            documentclass_pattern = get_command_pattern(r'documentclass')
            match = documentclass_pattern.search(latex_code)
            if match:
                position = match.end()
                latex_code = latex_code[:position] + ja_full_block + latex_code[position:]
                logger.info("Injected luatexja for Japanese")
        return _fix_page_overflow_for_cjk(latex_code)
    elif lang in ("ru", "uk", "bg", "sr", "mk", "be"):
        # Cyrillic languages: use fontspec + CMU Serif for proper Cyrillic rendering
        return add_cyrillic_font_support(latex_code, target_language)
    else:
        # Latin-script languages (en, de, fr, es, pt, it, nl, pl, etc.):
        # Zero-touch pass-through: We preserve Native pdflatex packages like T1 fontenc.
        # This completely drops the aggressive pdflatex primitive removals.
        logger.debug(f"Zero-touch pass-through for Latin-script language: {target_language}")
        return latex_code




def find_main_tex_file(dir):
    """
    Find the main LaTeX file in the given directory.
    
    Looks for 00README.json first, then searches for files with \\documentclass.
    """
    readme_path = os.path.join(dir, '00README.json')
    if os.path.exists(readme_path):
        config = read_json_file(readme_path)
        for source in config.get("sources", []):
            if source.get("usage") == "toplevel":
                main_file_name = source.get("filename")
                main_file_path = os.path.join(dir, main_file_name)
                return main_file_path if os.path.exists(main_file_path) else None

    tex_files = find_tex_files(dir)
    documentclass_pattern = re.compile(r"\\document(class|style)(\[.*?\])?\{.*?\}", re.DOTALL)
    
    for tex_file in tex_files:
        with open(tex_file, 'r', encoding='utf-8') as f:
            latex_code = f.read()
        latex_code = remove_comments(latex_code)
        
        if not documentclass_pattern.search(latex_code):
            continue

        return tex_file
    
    return None


def merge_tex_from_inputs(main_file_path):
    """
    Merge all \\input and \\include files into a single LaTeX document.
    """
    if main_file_path is None:
        return None
    dirname = os.path.dirname(main_file_path)
    maincontent = read_tex_file(main_file_path)
    maincontent = remove_comments(maincontent)
    pattern_input = re.compile(r'\\(input|include){(.*?)}')
    
    while True:
        result = pattern_input.search(maincontent)
        if result is None:
            break
        begin, end = result.span()
        match = result.group(2)
        inputfilepath = os.path.join(dirname, match)
        
        if match.endswith('.tex'):
            if os.path.exists(f'{inputfilepath}'):
                inputfilepath = f'{inputfilepath}'
            else:
                raise FileNotFoundError(f"File not found: {inputfilepath}")
        else:
            if os.path.exists(f'{inputfilepath}.tex'):
                inputfilepath = f'{inputfilepath}.tex'
            else:
                raise FileNotFoundError(f"File not found: {inputfilepath}.tex")
        
        input_tex = read_tex_file(inputfilepath)
        input_tex = remove_comments(input_tex)
        maincontent = maincontent[:begin] + input_tex + maincontent[end:]

    return maincontent


def save_to_tex(data, output_file):
    """Save data to .tex file"""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(data)


def save_to_json(data, output_file):
    """Save data to JSON file"""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def compile_with_latexmk(tex_file: str, out_dir: str = "out", engine: str = "pdflatex"):
    """
    Compile LaTeX file using latexmk (deprecated - use compiler.py instead)
    """
    os.makedirs(out_dir, exist_ok=True)
    
    cmd = [
        "latexmk",
        f"-{engine}",
        "-interaction=nonstopmode",
        f"-outdir={out_dir}",
        f"-synctex=1",
        f"-f",
        tex_file
    ]
    
    try:
        subprocess.run(cmd, check=True)
        logger.info("✅ Compilation successful")
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Compilation failed: {e}")


def collect_latex_errors_with_logpath(folder: str):
    """
    Collect LaTeX compilation errors from log files in project folders.
    """
    error_keyword = re.compile(r"latex error", re.IGNORECASE)
    summary = {}
    error_project_count = 0

    for project_name in os.listdir(folder):
        project_path = os.path.join(folder, project_name)
        if not os.path.isdir(project_path):
            continue

        preferred_builds = ["build_pdflatex", "build"]
        build_path = None
        for build_dir in preferred_builds:
            candidate = os.path.join(project_path, build_dir)
            if os.path.isdir(candidate):
                build_path = candidate
                break

        if build_path is None:
            continue

        log_files = [f for f in os.listdir(build_path) if f.endswith(".log")]
        if not log_files:
            continue

        log_path = os.path.join(build_path, log_files[0])
        try:
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                error_count = len(error_keyword.findall(content))
        except Exception as e:
            logger.error(f"Error reading {log_path}: {e}")
            continue

        if error_count > 0:
            summary[project_name] = {
                "total_errors": error_count,
                "log_path": log_path
            }
            error_project_count += 1

    output_path = os.path.join(folder, "latex_error_summary.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    logger.info(f"Summary saved to: {output_path}")
    logger.info(f"🔍 Total projects with LaTeX errors: {error_project_count}")


# ============================================================================
# arXiv Download Utilities (Web-adapted, Streamlit removed)
# ============================================================================

def get_tex_url(arxiv_id: str, headers: dict) -> str:
    """
    Get TeX source download link from arXiv
    """
    abs_url = f"https://arxiv.org/abs/{arxiv_id}"
    try:
        resp = requests.get(abs_url, headers=headers, timeout=10)
        resp.raise_for_status()
    except requests.RequestException:
        return ""
    
    soup = BeautifulSoup(resp.text, "html.parser")
    link = soup.find("a", class_="abs-button download-eprint")
    if link and link.get("href"):
        return f"https://arxiv.org{link['href']}"
    return ""


def is_already_downloaded(arxiv_id: str, save_dir: str) -> bool:
    """
    Check if arxiv paper source is already fully downloaded and extracted.

    Returns True only when the extracted subdirectory exists AND contains at
    least one .tex file, which proves the tar.gz was fully extracted.

    A bare .tar.gz (from a previous interrupted download/extract) or an empty
    extracted directory are treated as NOT downloaded so the pipeline can
    restart the download cleanly.
    """
    extracted_dir = os.path.join(save_dir, arxiv_id)
    if not os.path.isdir(extracted_dir):
        return False
    tex_files = find_tex_files(extracted_dir)
    return len(tex_files) > 0


class DownloadProgressCallback:
    """进度回调类，用于在下载过程中更新任务进度"""
    
    def __init__(self, task_manager=None, task_id: str = None, stage: str = "downloading"):
        """
        Args:
            task_manager: TaskManager 实例
            task_id: 任务 ID
            stage: 当前阶段名称 (downloading, extracting, downloading_pdf, validating)
        """
        self.task_manager = task_manager
        self.task_id = task_id
        self.stage = stage
        # 定义各阶段的进度范围
        self.stage_ranges = {
            "downloading": (0, 30),      # 下载 TeX 源码 0-30%
            "extracting": (30, 60),       # 解压文件 30-60%
            "downloading_pdf": (60, 80),  # 下载 PDF 60-80%
            "validating": (80, 100)       # 验证文件 80-100%
        }
        # 节流：记录上次上报的整数进度，避免对每个数据块都触发 Supabase 写入
        self._last_reported_progress: int = -1
    
    def update(self, current: int, total: int):
        """
        更新进度
        
        Args:
            current: 当前进度
            total: 总量
        """
        if not self.task_manager or not self.task_id:
            return
        
        start, end = self.stage_ranges.get(self.stage, (0, 100))
        stage_progress = (current / total) if total > 0 else 0
        overall_progress = int(start + (end - start) * stage_progress)

        # 节流：仅在整数进度发生变化或下载/解压完成时才上报，
        # 避免对每个 8KB 数据块都触发一次同步 Supabase 写操作。
        is_complete = (current >= total)
        if overall_progress <= self._last_reported_progress and not is_complete:
            return
        self._last_reported_progress = overall_progress

        # 获取阶段描述
        stage_descriptions = {
            "downloading": "正在下载 TeX 源码",
            "extracting": "正在解压文件",
            "downloading_pdf": "正在下载 PDF",
            "validating": "正在验证文件"
        }
        message = f"{stage_descriptions.get(self.stage, self.stage)}: {int(stage_progress * 100)}%"

        self.task_manager.update_task(
            task_id=self.task_id,
            progress=overall_progress,
            stage=self.stage,
            message=message
        )


def download_tex(arxiv_id: str, tex_url: str, save_dir: str, headers: dict, progress_callback=None):
    """
    Download TeX source .tar.gz file with progress tracking
    
    Args:
        arxiv_id: arXiv paper ID
        tex_url: URL to TeX source
        save_dir: Directory to save files
        headers: HTTP headers
        progress_callback: Optional DownloadProgressCallback instance
    """
    # Ensure save directory exists
    os.makedirs(save_dir, exist_ok=True)
    
    file_path = os.path.join(save_dir, f"{arxiv_id}.tar.gz")

    try:
        with requests.get(tex_url, headers=headers, stream=True, timeout=20) as r:
            r.raise_for_status()
            total_size = int(r.headers.get("Content-Length", 0))
            downloaded = 0

            with open(file_path, "wb") as f:
                for chunk in r.iter_content(8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        # 使用回调更新进度
                        if progress_callback:
                            progress_callback.update(downloaded, total_size)
        
        logger.info(f"[SUCCESS] {arxiv_id} successfully downloaded to {file_path}.")
        
        # 更新进度到解压阶段
        if progress_callback:
            progress_callback.stage = "extracting"
            progress_callback.update(0, 1)
        
        # Extract the tar.gz file
        extract_dir = os.path.join(save_dir, arxiv_id)
        os.makedirs(extract_dir, exist_ok=True)
        
        try:
            # Use 'r:*' to auto-detect compression format (supports gz, bz2, xz, or plain tar)
            # This is crucial because arXiv files may have .tar.gz extension but use different compression
            with tarfile.open(file_path, mode='r:*') as tar:
                members = tar.getmembers()
                total_members = len(members)
                # Filter for security - avoid absolute paths and path traversal
                for i, member in enumerate(members):
                    if member.name.startswith('/') or '..' in member.name:
                        logger.warning(f"Skipping potentially unsafe path: {member.name}")
                        continue
                    tar.extract(member, path=extract_dir)
                    # 每解压一个文件更新一次进度
                    if progress_callback and total_members > 0:
                        progress_callback.update(i + 1, total_members)
            logger.info(f"[SUCCESS] {arxiv_id} extracted to {extract_dir}")
            
            # Remove the tar.gz file after extraction
            os.remove(file_path)
            logger.debug(f"Removed tar.gz file: {file_path}")
            
        except tarfile.ReadError as e:
            # Sometimes arXiv returns a single TeX file without tar wrapper
            logger.warning(f"[WARN] {file_path} is not a valid tar archive, trying as gzip: {e}")
            try:
                import gzip
                # Try to decompress as plain gzip file
                with gzip.open(file_path, 'rb') as gz_file:
                    content = gz_file.read()
                    # Check if it's a single TeX file
                    if content.startswith(b'%') or b'\\documentclass' in content[:1024]:
                        tex_file_path = os.path.join(extract_dir, f"{arxiv_id}.tex")
                        with open(tex_file_path, 'wb') as f:
                            f.write(content)
                        logger.info(f"[SUCCESS] Single TeX file extracted to {tex_file_path}")
                        os.remove(file_path)
                    else:
                        logger.error(f"[FAIL] Unknown file format for {file_path}")
                        return None
            except Exception as inner_e:
                logger.error(f"[FAIL] Failed to extract {file_path} as gzip: {inner_e}")
                return None
        except tarfile.TarError as e:
            logger.error(f"[FAIL] Failed to extract {file_path}: {e}")
            return None
        
        return extract_dir

    except requests.RequestException as e:
        logger.error(f"[FAIL] {arxiv_id} download failed: {e}")
        return None


def batch_download_arxiv_tex(
    arxiv_ids: List[str], 
    save_dir: str = "./tex_sources",
    task_manager=None,
    task_id: str = None
):
    """
    Batch download multiple arXiv paper TeX sources with progress tracking
    
    Args:
        arxiv_ids: List of arXiv IDs to download
        save_dir: Directory to save sources
        task_manager: Optional TaskManager instance for progress updates
        task_id: Optional task ID for tracking
    """
    source_dirs = []
    headers = {"User-Agent": "Mozilla/5.0"}
    for arxiv_id in arxiv_ids:
        if is_already_downloaded(arxiv_id, save_dir):
            source_dirs.append(os.path.join(save_dir, arxiv_id))
            logger.info(f"[SKIP] Already downloaded: {arxiv_id}")
            continue

        tex_url = get_tex_url(arxiv_id, headers)
        if tex_url:
            # 创建下载阶段的进度回调
            download_callback = DownloadProgressCallback(
                task_manager=task_manager,
                task_id=task_id,
                stage="downloading"
            ) if task_manager and task_id else None
            
            dir = download_tex(arxiv_id, tex_url, save_dir, headers, download_callback)
            if dir:  # Only add if download and extraction succeeded
                source_dirs.append(dir)
            else:
                logger.error(f"[FAIL] Failed to download or extract {arxiv_id}")
                continue
        else:
            logger.warning(f"[SKIP] No TeX source found for {arxiv_id}. Please check the arXiv ID or the availability of the source.")
            continue

        # 更新进度到 PDF 下载阶段
        if task_manager and task_id:
            pdf_callback = DownloadProgressCallback(
                task_manager=task_manager,
                task_id=task_id,
                stage="downloading_pdf"
            )
            pdf_callback.update(0, 1)
        
        # Download PDF file
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        pdf_path = os.path.join(save_dir, arxiv_id, f"{arxiv_id}.pdf")
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

        try:
            # 使用流式下载以支持进度更新
            with requests.get(pdf_url, headers=headers, stream=True, timeout=30) as response:
                response.raise_for_status()
                total_size = int(response.headers.get('Content-Length', 0))
                downloaded = 0
                
                with open(pdf_path, 'wb') as f:
                    for chunk in response.iter_content(8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            # 更新 PDF 下载进度
                            if task_manager and task_id and total_size > 0:
                                pdf_callback.update(downloaded, total_size)
            
            logger.info(f"[SUCCESS] Downloaded PDF for {arxiv_id}")
            
            # PDF 下载完成，确保进度到达 100%
            if task_manager and task_id:
                pdf_callback.update(1, 1)
        except Exception as e:
            logger.error(f"[ERROR] Failed to download PDF for {arxiv_id}: {str(e)}")
        
        # 验证阶段
        if task_manager and task_id:
            validating_callback = DownloadProgressCallback(
                task_manager=task_manager,
                task_id=task_id,
                stage="validating"
            )
            validating_callback.update(0, 1)
            
            # 验证 .tex 文件是否存在
            tex_files = find_tex_files(dir) if dir else []
            if tex_files:
                logger.info(f"[SUCCESS] Validated {len(tex_files)} .tex files for {arxiv_id}")
            
            # 验证完成
            validating_callback.update(1, 1)

    return source_dirs


def get_arxiv_category(arxiv_ids: List[str]) -> dict:
    """Get arXiv categories for papers"""
    results = {}
    headers = {"User-Agent": "Mozilla/5.0"}
    for arxiv_id in arxiv_ids:
        abs_url = f"https://arxiv.org/abs/{arxiv_id}"
        categories = []

        try:
            resp = requests.get(abs_url, headers=headers, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            subjects_div = soup.find("div", class_="subjects")
            if subjects_div:
                matches = re.findall(r"\(([a-z]+\.[A-Z]+)\)", subjects_div.text)
                categories.extend(matches)
            else:
                td_subjects = soup.find("td", class_="tablecell subjects")
                if td_subjects:
                    matches = re.findall(r'\(([a-z]+\.[A-Z]+)\)', td_subjects.text)
                    categories.extend(matches)

            if not categories:
                logger.warning(f"No categories found for {arxiv_id}")

        except requests.RequestException as e:
            logger.error(f"Failed to fetch {arxiv_id}: {e}")
            categories = []

        results[arxiv_id] = (categories)
        time.sleep(1)

    return results


def is_valid_arxiv_id(id_str):
    """Validate arXiv ID format"""
    # Modern format: YYYY.NNNNN or YYYY.NNNNNNN
    if re.match(r'^\d{4}\.\d{5,7}$', id_str):
        return True
    # Old format: subject/YYMMNNN (e.g., hep-th/9901001)
    if re.match(r'^[\w\-]+/\d{7}$', id_str):
        return True
    return False


def extract_arxiv_ids(arxiv_input):
    """
    Extract valid arXiv IDs from string or list of strings/URLs
    
    Args:
        arxiv_input: Single string or list of strings containing arXiv IDs/URLs
        
    Returns:
        List of validated arXiv IDs
        
    Examples:
        >>> extract_arxiv_ids("2508.18791")
        ['2508.18791']
        >>> extract_arxiv_ids("https://arxiv.org/abs/2508.18791")
        ['2508.18791']
        >>> extract_arxiv_ids(["2508.18791", "https://arxiv.org/pdf/1234.56789.pdf"])
        ['2508.18791', '1234.56789']
    """
    # 统一转换为列表处理
    if isinstance(arxiv_input, str):
        arxiv_input = [arxiv_input]
    
    ids = []
    for item in arxiv_input:
        if is_valid_arxiv_id(item):
            ids.append(item)
            continue

        url_pattern = r'(?:arxiv\.org/)(?:abs|pdf|e-print)/([\w\-]+/\d{7}|\d{4}\.\d{5,7})(?:\.pdf)?'
        match = re.search(url_pattern, item)
        if match:
            ids.append(match.group(1))
    return ids


# ---------------------------------------------------------------------------
# Typography Formatting Config Injection
# ---------------------------------------------------------------------------

# Geometry margin presets for LaTeX geometry package
_MARGIN_PRESETS = {
    "narrow": "left=1.5cm,right=1.5cm,top=2cm,bottom=2cm",
    "normal": "left=2.5cm,right=2.5cm,top=2.5cm,bottom=2.5cm",
    "wide":   "left=3.5cm,right=3.5cm,top=3cm,bottom=3cm",
}

# CJK font mapping to TeX Live 2025 font names
_CJK_FONT_MAP = {
    "songti": ("FandolSong", "FandolSong Bold", "FandolSong"),
    "heiti":  ("FandolHei",  "FandolHei Bold",  "FandolHei"),
}


def _has_package(latex_code: str, pkg: str) -> bool:
    """Check whether a LaTeX package is already loaded (rough string match)."""
    return bool(re.search(rf'\\usepackage(?:\[[^\]]*\])?\{{{re.escape(pkg)}\}}', latex_code))


def _inject_after_documentclass(latex_code: str, block: str) -> str:
    """Insert *block* immediately after the \\documentclass{...} command."""
    pattern = get_command_pattern(r'documentclass')
    match = pattern.search(latex_code)
    if match:
        pos = match.end()
        return latex_code[:pos] + "\n" + block + latex_code[pos:]
    # Fallback: prepend to preamble area (before \begin{document})
    begin_doc = re.search(r'\\begin\s*\{document\}', latex_code)
    if begin_doc:
        pos = begin_doc.start()
        return latex_code[:pos] + block + "\n" + latex_code[pos:]
    return block + "\n" + latex_code


def _inject_after_begin_document(latex_code: str, block: str) -> str:
    """Insert *block* immediately after \\begin{document}."""
    match = re.search(r'\\begin\s*\{document\}', latex_code)
    if match:
        pos = match.end()
        return latex_code[:pos] + "\n" + block + latex_code[pos:]
    return latex_code + "\n" + block


def _inject_after_cjk_package(latex_code: str, block: str) -> str:
    """Insert *block* immediately after the CJK package (ctex or xeCJK).

    The \\setCJKmainfont family of commands requires xeCJK to be loaded first.
    When ctex is used, it automatically loads xeCJK, so we can safely inject
    after ctex.  If neither package is found, fall back to injecting right
    before \\begin{document} (preamble end).
    """
    # Try ctex first (most common for zh translations)
    for pkg_pattern in [
        r'\\usepackage(?:\[[^\]]*\])?\{ctex\}',
        r'\\usepackage(?:\[[^\]]*\])?\{xeCJK\}',
    ]:
        match = re.search(pkg_pattern, latex_code)
        if match:
            pos = match.end()
            return latex_code[:pos] + "\n" + block + latex_code[pos:]

    # Fallback: just before \begin{document}
    begin_doc = re.search(r'\\begin\s*\{document\}', latex_code)
    if begin_doc:
        pos = begin_doc.start()
        return latex_code[:pos] + block + "\n" + latex_code[pos:]

    return _inject_after_documentclass(latex_code, block)

# ---------------------------------------------------------------------------
# Document-class font size restrictions
# Keys are LaTeX class names; values are sets of supported pt sizes.
# Used by apply_formatting_config() to auto-downgrade unsafe values.
# ---------------------------------------------------------------------------
_RESTRICTED_DOCCLASSES: Dict[str, set] = {
    "revtex4-2":   {10, 12},
    "revtex4-1":   {10, 12},
    "revtex4":     {10, 12},
    "IEEEtran":    {9, 10, 11, 12},
    "elsarticle":  {10, 11, 12},
    "svjour3":     {10},
    "spie":        {10, 12},
    "aastex":      {10, 12},
    "aastex62":    {10, 12},
}


def _detect_docclass(latex_code: str) -> str:
    """Extract document class name from \\documentclass command."""
    m = re.search(r'\\documentclass(?:\[[^\]]*\])?\{([^}]+)\}', latex_code)
    return m.group(1).strip() if m else ""


def _nearest_allowed_size(requested: float, allowed: set) -> int:
    """Return the size in *allowed* closest to *requested*."""
    return min(allowed, key=lambda x: abs(x - requested))


def apply_formatting_config(latex_code: str, config) -> tuple:
    """
    Inject typography formatting commands into the LaTeX preamble based on
    FormattingConfig settings.

    This function is called after add_cjk_package() (in GeneratorAgent.execute)
    and before LaTeX compilation. It follows the same anchor-locate + regex-inject
    pattern used by add_cjk_package() / add_ctex_package().

    Args:
        latex_code: Full LaTeX source code (preamble + body).
        config: FormattingConfig instance (or dict-like with .get() support).
                If None or all fields are None, the original code is returned unchanged.

    Returns:
        (modified_latex_code, list_of_warning_messages)
        Callers should pass warnings to task_manager.update_task(warnings=...)
    """
    fmt_warnings: list = []

    if config is None:
        return latex_code, fmt_warnings

    # Support both Pydantic model and plain dict
    def _get(field, default=None):
        if hasattr(config, field):
            return getattr(config, field)
        if isinstance(config, dict):
            return config.get(field, default)
        return default

    line_spacing    = _get("line_spacing")
    font_size       = _get("font_size")
    cjk_font        = _get("cjk_font")
    column_mode     = _get("column_mode")
    margin          = _get("margin")
    paragraph_indent = _get("paragraph_indent")
    bib_style       = _get("bib_style")
    cite_style      = _get("cite_style")
    localize_captions = _get("localize_captions")

    # Early exit: nothing to do
    if all(v is None for v in [
        line_spacing, font_size, cjk_font, column_mode,
        margin, paragraph_indent, bib_style, cite_style, localize_captions
    ]):
        return latex_code, fmt_warnings

    logger.info(f"apply_formatting_config: applying {config!r}")

    # -----------------------------------------------------------------------
    # 1. Line spacing — inject setspace package + \setstretch{}
    # -----------------------------------------------------------------------
    if line_spacing is not None:
        # ── Validate line spacing range ─────────────────────────────────────
        if line_spacing < 1.0 or line_spacing > 2.5:
            warn_msg = (
                f"行间距 {line_spacing} 超出安全范围 [1.0, 2.5]，"
                f"已跳过注入以避免排版异常"
            )
            fmt_warnings.append(warn_msg)
            logger.warning(f"[apply_formatting_config] {warn_msg}")
            line_spacing = None  # skip injection

    if line_spacing is not None:
        spacing_block = ""
        if not _has_package(latex_code, "setspace"):
            spacing_block += "\\usepackage{setspace}\n"
        # Replace existing \setstretch or \doublespacing/\onehalfspacing, else inject
        existing = re.search(r'\\(?:setstretch|doublespacing|onehalfspacing|singlespacing)\b[^\n]*', latex_code)
        if existing:
            latex_code = latex_code[:existing.start()] + f"\\setstretch{{{line_spacing}}}" + latex_code[existing.end():]
        else:
            spacing_block += f"\\setstretch{{{line_spacing}}}\n"
        if spacing_block:
            latex_code = _inject_after_documentclass(latex_code, spacing_block.rstrip())
        logger.debug(f"Injected line_spacing={line_spacing}")

    # -----------------------------------------------------------------------
    # 2. Font size — replace/add pt option in \documentclass[...]{...}
    # -----------------------------------------------------------------------
    if font_size is not None:
        # ── Validate / auto-downgrade font size ──────────────────────────────
        docclass = _detect_docclass(latex_code)
        restricted = _RESTRICTED_DOCCLASSES.get(docclass)
        if restricted and int(font_size) not in restricted:
            safe = _nearest_allowed_size(font_size, restricted)
            warn_msg = (
                f"字号 {font_size:g}pt 与文档类 '{docclass}' 不兼容（仅支持 "
                f"{sorted(restricted)}pt），已自动调整为 {safe}pt"
            )
            fmt_warnings.append(warn_msg)
            logger.warning(f"[apply_formatting_config] {warn_msg}")
            font_size = float(safe)
        elif font_size < 8 or font_size > 14:
            warn_msg = (
                f"字号 {font_size:g}pt 超出安全范围 [8, 14]pt，"
                f"已跳过注入以避免编译错误"
            )
            fmt_warnings.append(warn_msg)
            logger.warning(f"[apply_formatting_config] {warn_msg}")
            font_size = None  # skip injection entirely

    if font_size is not None:
        pt_str = f"{font_size:g}pt"
        # Match \documentclass[...Xpt...]{...} and replace the Xpt part
        def _replace_fontsize(m):
            opts = m.group(0)
            # Remove any existing Xpt
            opts = re.sub(r'\d+(?:\.\d+)?pt', '', opts)
            # Insert new size after opening bracket
            opts = re.sub(r'\[', f"[{pt_str},", opts, count=1)
            # Clean up double commas
            opts = re.sub(r',\s*,', ',', opts)
            opts = re.sub(r'\[,', '[', opts)
            return opts

        latex_code = re.sub(r'\[[^\]]*\d+(?:\.\d+)?pt[^\]]*\]', _replace_fontsize, latex_code, count=1)

        # If no existing pt option, add it to documentclass options
        if pt_str not in latex_code:
            def _add_fontsize(m):
                full = m.group(0)
                # Has options bracket
                if '[' in full:
                    return re.sub(r'\[', f"[{pt_str},", full, count=1)
                # No options: insert before {classname}
                brace_pos = full.index('{')
                return full[:brace_pos] + f"[{pt_str}]" + full[brace_pos:]
            latex_code = re.sub(
                r'\\documentclass(?:\[[^\]]*\])?\{[^}]+\}',
                _add_fontsize,
                latex_code,
                count=1
            )
        logger.debug(f"Injected font_size={font_size}pt")

    # -----------------------------------------------------------------------
    # 3. CJK font — \setCJKmainfont / \setCJKsansfont / \setCJKmonofont
    #    MUST be placed AFTER \usepackage{ctex} or \usepackage{xeCJK} so that
    #    the xeCJK commands are available. Injecting after \documentclass would
    #    put them BEFORE ctex, causing them to render as plain text.
    # -----------------------------------------------------------------------
    if cjk_font is not None and cjk_font in _CJK_FONT_MAP:
        main, bold, mono = _CJK_FONT_MAP[cjk_font]
        font_block = (
            f"\\setCJKmainfont{{{main}}}[BoldFont={{{bold}}}]\n"
            f"\\setCJKsansfont{{{main}}}\n"
            f"\\setCJKmonofont{{{mono}}}\n"
        )
        # Replace existing \setCJKmainfont or inject after CJK package
        existing = re.search(r'\\setCJKmainfont[^\n]+\n?', latex_code)
        if existing:
            latex_code = latex_code[:existing.start()] + font_block + latex_code[existing.end():]
        else:
            latex_code = _inject_after_cjk_package(latex_code, font_block.rstrip())
        logger.debug(f"Injected cjk_font={cjk_font}")

    # -----------------------------------------------------------------------
    # 4. Column mode — single/double column switching
    # -----------------------------------------------------------------------
    if column_mode == "single":
        # Remove twocolumn from documentclass options
        latex_code = re.sub(
            r'(\\documentclass\[)([^\]]*)(twocolumn,?\s*|,?\s*twocolumn)([^\]]*\])',
            lambda m: m.group(1) + re.sub(r',?\s*twocolumn\s*,?', '', m.group(2) + m.group(4)).replace(',,', ',').strip(','),
            latex_code
        )
        # Remove \twocolumn command if present
        latex_code = re.sub(r'\\twocolumn\b[^\n]*\n?', '', latex_code)
        # Add \onecolumn after \begin{document} if it's not already there
        if '\\onecolumn' not in latex_code:
            latex_code = _inject_after_begin_document(latex_code, "\\onecolumn")
        logger.debug("Injected column_mode=single")

    elif column_mode == "double":
        # Add twocolumn to documentclass options if not present
        if 'twocolumn' not in latex_code:
            latex_code = re.sub(
                r'(\\documentclass\[)([^\]]*\])',
                lambda m: m.group(1) + "twocolumn," + m.group(2),
                latex_code,
                count=1
            )
            # If no options bracket, add one
            if 'twocolumn' not in latex_code:
                latex_code = re.sub(
                    r'(\\documentclass)(\{[^}]+\})',
                    r'\1[twocolumn]\2',
                    latex_code,
                    count=1
                )
        logger.debug("Injected column_mode=double")

    # -----------------------------------------------------------------------
    # 5. Page margins — geometry package
    # -----------------------------------------------------------------------
    if margin is not None and margin in _MARGIN_PRESETS:
        geo_opts = _MARGIN_PRESETS[margin]
        existing_geo = re.search(r'\\usepackage\[[^\]]*\]\{geometry\}', latex_code)
        if existing_geo:
            # Replace existing geometry options
            latex_code = latex_code[:existing_geo.start()] + \
                         f"\\usepackage[{geo_opts}]{{geometry}}" + \
                         latex_code[existing_geo.end():]
        else:
            latex_code = _inject_after_documentclass(latex_code, f"\\usepackage[{geo_opts}]{{geometry}}")
        logger.debug(f"Injected margin={margin}")

    # -----------------------------------------------------------------------
    # 6. Paragraph indent — \setlength{\parindent}{2em}
    # -----------------------------------------------------------------------
    if paragraph_indent is True:
        indent_cmd = "\\setlength{\\parindent}{2em}"
        existing = re.search(r'\\setlength\s*\{\\parindent\}[^\n]+', latex_code)
        if existing:
            latex_code = latex_code[:existing.start()] + indent_cmd + latex_code[existing.end():]
        else:
            latex_code = _inject_after_begin_document(latex_code, indent_cmd)
        logger.debug("Injected paragraph_indent=True")

    # -----------------------------------------------------------------------
    # 7. Bibliography style — replace \bibliographystyle{...}
    # -----------------------------------------------------------------------
    if bib_style is not None:
        # Map friendly names to actual BibTeX style names
        _BIB_STYLE_MAP = {
            "gbt7714-numerical":   "gbt7714-numerical",
            "gbt7714-author-year": "gbt7714-author-year",
            "ieeetr":              "ieeetr",
            "apalike":             "apalike",
        }
        actual_style = _BIB_STYLE_MAP.get(bib_style, bib_style)
        # Replace existing \bibliographystyle
        existing = re.search(r'\\bibliographystyle\{[^}]*\}', latex_code)
        if existing:
            latex_code = latex_code[:existing.start()] + \
                         f"\\bibliographystyle{{{actual_style}}}" + \
                         latex_code[existing.end():]
        else:
            # Inject before \bibliography{...} if it exists, otherwise before \end{document}
            bib_ref = re.search(r'\\bibliography\{', latex_code)
            if bib_ref:
                latex_code = latex_code[:bib_ref.start()] + \
                             f"\\bibliographystyle{{{actual_style}}}\n" + \
                             latex_code[bib_ref.start():]
        logger.debug(f"Injected bib_style={bib_style}")

    # -----------------------------------------------------------------------
    # 8. Citation style — natbib package
    # -----------------------------------------------------------------------
    if cite_style is not None:
        _CITE_STYLE_MAP = {
            "numbers":    "numbers",
            "super":      "super",
            "authoryear": "authoryear",
        }
        natbib_opt = _CITE_STYLE_MAP.get(cite_style, "numbers")
        existing_natbib = re.search(r'\\usepackage(?:\[[^\]]*\])?\{natbib\}', latex_code)
        if existing_natbib:
            # Replace options
            latex_code = latex_code[:existing_natbib.start()] + \
                         f"\\usepackage[{natbib_opt}]{{natbib}}" + \
                         latex_code[existing_natbib.end():]
        else:
            latex_code = _inject_after_documentclass(latex_code, f"\\usepackage[{natbib_opt}]{{natbib}}")
        logger.debug(f"Injected cite_style={cite_style}")

    # -----------------------------------------------------------------------
    # 9. Localize captions — \renewcommand\figurename{图} etc.
    # -----------------------------------------------------------------------
    if localize_captions is True:
        caption_block = (
            "\\renewcommand{\\figurename}{图}\n"
            "\\renewcommand{\\tablename}{表}\n"
            "\\renewcommand{\\abstractname}{摘要}\n"
            "\\renewcommand{\\contentsname}{目录}\n"
            "\\renewcommand{\\refname}{参考文献}\n"
            "\\renewcommand{\\appendixname}{附录}\n"
        )
        # Inject after \begin{document}
        if "\\renewcommand{\\figurename}" not in latex_code:
            latex_code = _inject_after_begin_document(latex_code, caption_block.rstrip())
        logger.debug("Injected localize_captions=True")

    return latex_code, fmt_warnings


# ---------------------------------------------------------------------------
# Task 12: Sensitive Command Pre-Translation Protection (Emergency Regex Masking)
# ---------------------------------------------------------------------------

# Registry of LaTeX commands/environments whose arguments MUST NOT be translated.
# Each entry is a compiled regex pattern.  Patterns are tried in order.
#
# Design notes:
#   - Use `regex` module (already imported) for possessive quantifiers that
#     handle deeply nested braces without catastrophic backtracking.
#   - CCSXML environment pattern spans multiple lines (regex.DOTALL).
PROTECTED_COMMANDS: List[re.Pattern] = [
    # \begin{CCSXML}...\end{CCSXML}  — ACM CCS XML block (multi-line)
    regex.compile(
        r'\\begin\{CCSXML\}.*?\\end\{CCSXML\}',
        regex.DOTALL,
    ),
    # \ccsdesc[optional]{...}  — ACM CCS descriptor (nested braces allowed)
    regex.compile(
        r'\\ccsdesc(?:\[[^\[\]]*\])?\{(?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*\}',
        regex.DOTALL,
    ),
    # \received[optional]{...}  — ACM received date
    regex.compile(
        r'\\received(?:\[[^\[\]]*\])?\{(?:[^{}]|\{[^{}]*\})*\}',
        regex.DOTALL,
    ),
    # \keywords{...}  — ACM keywords block
    regex.compile(
        r'\\keywords\{(?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*\}',
        regex.DOTALL,
    ),
]

_PLACEHOLDER_PREFIX = "PROTECTED_CMD"
# Primary exact-match pattern
_PLACEHOLDER_RE = re.compile(r'<PROTECTED_CMD_(\d+)>')
# Fuzzy pattern to tolerate common LLM mutations of the placeholder:
#   \protect\PROTECTED_CMD_N, {\PROTECTED_CMD_N}, \\PROTECTED_CMD_N, etc.
_PLACEHOLDER_FUZZY_RE = re.compile(
    r'(?:'
    r'\\\\protect\\\\?\s*|'   # \protect\ prefix
    r'\\\\(?:protect)?\\\\?\s*|'  # \\ prefix
    r'\\?'                   # optional backslash
    r')'
    r'(?:[{<])?'             # optional { or <
    r'PROTECTED_CMD_(\d+)'   # capture the index
    r'(?:[}>])?',            # optional } or >
    re.IGNORECASE,
)


def mask_sensitive_commands(
    content: str,
    registry: Optional[List] = None,
) -> Tuple[str, Dict[str, str]]:
    """
    Mask sensitive LaTeX commands before sending content to an LLM.

    Replaces each match of every pattern in *registry* with an opaque
    placeholder of the form ``<PROTECTED_CMD_N>``.  The mapping from
    placeholder back to original text is returned so the caller can restore
    the originals after translation.

    Args:
        content:  The raw LaTeX text to process.
        registry: Optional list of compiled regex patterns.  Defaults to
                  the module-level ``PROTECTED_COMMANDS`` list.

    Returns:
        A ``(masked_content, mapping)`` tuple where *mapping* maps each
        placeholder string to its original matched text.
    """
    if not content:
        return content, {}

    if registry is None:
        registry = PROTECTED_COMMANDS

    mapping: Dict[str, str] = {}
    counter = [0]  # mutable so nested closure can increment

    def _replace(m: re.Match) -> str:
        placeholder = f"<{_PLACEHOLDER_PREFIX}_{counter[0]}>"
        mapping[placeholder] = m.group(0)
        counter[0] += 1
        return placeholder

    masked = content
    for pattern in registry:
        masked = pattern.sub(_replace, masked)

    if mapping:
        logger.debug(
            "mask_sensitive_commands: masked %d region(s): %s",
            len(mapping),
            list(mapping.keys()),
        )

    return masked, mapping


def unmask_sensitive_commands(
    translated_content: str,
    mapping: Dict[str, str],
) -> str:
    """
    Restore sensitive LaTeX commands after LLM translation.

    Three-stage hardened restoration:
    1. Exact match: replace ``<PROTECTED_CMD_N>`` with original from mapping.
    2. Fuzzy match: handle LLM mutations like ``\\protect\\PROTECTED_CMD_N``,
       ``{\\PROTECTED_CMD_N}``, ``\\\\PROTECTED_CMD_N`` etc.
    3. Residual scan: if any ``PROTECTED_CMD_N`` substring still remains,
       force-restore by index order from the sorted mapping.

    Args:
        translated_content: The translated text that may contain placeholders.
        mapping: The ``{placeholder: original}`` dict returned by
                 :func:`mask_sensitive_commands`.

    Returns:
        The restored string.
    """
    if not translated_content or not mapping:
        return translated_content

    # Build a lookup from index → (placeholder, original)
    index_map: Dict[int, tuple] = {}
    for ph, original in mapping.items():
        m = _PLACEHOLDER_RE.match(ph)
        if m:
            index_map[int(m.group(1))] = (ph, original)

    # --- Stage 1: Exact match ---
    def _restore_exact(m: re.Match) -> str:
        placeholder = m.group(0)
        original = mapping.get(placeholder)
        if original is None:
            logger.warning(
                "unmask_sensitive_commands [exact]: placeholder %s not found in mapping",
                placeholder,
            )
            return placeholder
        return original

    restored = _PLACEHOLDER_RE.sub(_restore_exact, translated_content)

    # --- Stage 2: Fuzzy match (if any PROTECTED_CMD text remains) ---
    if "PROTECTED_CMD" in restored:
        fuzzy_restored_count = [0]

        def _restore_fuzzy(m: re.Match) -> str:
            idx = int(m.group(1))
            entry = index_map.get(idx)
            if entry is None:
                logger.warning(
                    "unmask_sensitive_commands [fuzzy]: index %d not found in mapping",
                    idx,
                )
                return m.group(0)
            fuzzy_restored_count[0] += 1
            logger.warning(
                "unmask_sensitive_commands [fuzzy]: restored mutated placeholder "
                "PROTECTED_CMD_%d via fuzzy match (matched: %r)",
                idx,
                m.group(0),
            )
            return entry[1]

        restored = _PLACEHOLDER_FUZZY_RE.sub(_restore_fuzzy, restored)
        if fuzzy_restored_count[0]:
            logger.info(
                "unmask_sensitive_commands: fuzzy stage restored %d placeholder(s)",
                fuzzy_restored_count[0],
            )

    # --- Stage 3: Residual scan by positional order ---
    if "PROTECTED_CMD" in restored and index_map:
        remaining_indices = sorted(index_map.keys())
        for idx in remaining_indices:
            ph, original = index_map[idx]
            # Try to find any remaining occurrence of "PROTECTED_CMD_<idx>" text
            residual_pattern = re.compile(rf'PROTECTED_CMD_{idx}(?!\d)', re.IGNORECASE)
            if residual_pattern.search(restored):
                restored = residual_pattern.sub(lambda _m, orig=original: orig, restored)
                logger.warning(
                    "unmask_sensitive_commands [residual]: force-restored "
                    "PROTECTED_CMD_%d by positional scan",
                    idx,
                )

    # Final warning: if any PROTECTED_CMD text remains, it could not be restored
    if "PROTECTED_CMD" in restored:
        logger.error(
            "unmask_sensitive_commands: could not restore all PROTECTED_CMD "
            "placeholders; residual text remains in output"
        )

    return restored


def restore_mangled_placeholders(tex_content: str, expected_phs: list) -> str:
    import re
    restored_tex = tex_content
    for expected_ph in expected_phs:
        if expected_ph in restored_tex:
            continue
        inner_content = expected_ph.strip('<>')
        parts = inner_content.split('_')
        escaped_parts = []
        for p in parts:
            # Allow optional spaces or common junk between characters in the name (e.g. PLACE HOLDER)
            char_pattern = r'[_\$§#\* ]*'
            escaped_p = char_pattern.join([f'(?:{re.escape(c)}|\\\\{re.escape(c)})' for c in p])
            escaped_parts.append(escaped_p)
        separator = r'(?:\\?[_\$§#\* ]|\s)+'
        flexible_inner = separator.join(escaped_parts)
        
        # Prevent prefix matching (e.g., `ENV_1` matching `ENV_10` due to optional suffix)
        # Assumes placeholders end with numbers or letters (e.g., `begin`). 
        # For numeric endings, the very next char should not be another digit.
        flexible_inner += r'(?!\s*[0-9])'
        
        # Greedily consume any accidental math delimiters ($) or angle brackets added by the LLM
        prefix = r'(?:[\$<]|\\[\$<]|\\textless|\\langle)*\s*'
        suffix = r'\s*(?:[\$>]|\\[\$>]|\\textgreater|\\rangle)*'
        pattern = prefix + flexible_inner + suffix
        regex = re.compile(pattern, re.IGNORECASE)
        def replacement(match):
            return expected_ph
        # print('Compiling:', pattern)
        restored_tex, count = regex.subn(replacement, restored_tex)
    return restored_tex

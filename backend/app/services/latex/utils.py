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
    newcommand = rf'\\(?:newcommand\*?|def|renewcommand|newenvironment|renewenvironment){spaces}(?:\{{\\([a-zA-Z]+)\}}|\\([a-zA-Z]+)){spaces}(?:\[(\d)\])?{spaces}({get_pattern_brace(4)})'
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


def add_ctex_package(latex_code):
    """Add ctex package for Chinese support and handle XeLaTeX compatibility"""
    if "\\usepackage[UTF8]{ctex}" not in latex_code:
        ctex_package = "\\usepackage[UTF8]{ctex}"
        documentclass = r'documentclass'
        documentclass_pattern = get_command_pattern(documentclass)
        match = documentclass_pattern.search(latex_code)
        if match:
            position = match.end()
            latex_code = latex_code[:position] + "\n" + ctex_package + "\n" + latex_code[position:]
    
    # Comment out pdfLaTeX-specific commands for XeLaTeX compatibility
    latex_code = _comment_out_pdflatex_commands(latex_code)
    
    return latex_code


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


def add_ja_package(latex_code):
    """Add Japanese package support"""
    if "\\usepackage{luatex-ja}" not in latex_code:
        ctex_package = "\\usepackage{luatexja}"
        documentclass = r'documentclass'
        documentclass_pattern = get_command_pattern(documentclass)
        match = documentclass_pattern.search(latex_code)
        if match:
            position = match.end()
            latex_code = latex_code[:position] + "\n" + ctex_package + "\n" + latex_code[position:]
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
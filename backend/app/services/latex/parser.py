"""
LaTeX Parser with AST Processing

Adapted from prototype system with:
- All Streamlit dependencies removed  
- Progress callback mechanism added
- Python logging integrated
- sys.stderr redirection removed
"""

from typing import Any, Dict, Optional, Callable, List
from .utils import *
import tiktoken
import logging
import re

logger = logging.getLogger(__name__)


_PLACEHOLDER_ATOM_RE = re.compile(
    r"<(?:PLACEHOLDER_[^>]+|ENV(?:_BEGIN|_END)?_[^>]+|ITEM_[^>]+|EQROW_[^>]+|INLMATH_[^>]+)>"
)
_LATEX_COMMAND_TOKEN_RE = re.compile(r"\\(?:[A-Za-z@]+|\S)")
_STRUCTURAL_SYMBOL_RE = re.compile(r"[\{\}\[\]\(\)\$&_^~%#]")
_SECTION_CHUNK_ID_RE = re.compile(r"^(?P<base>.+)_chunk_\d+$")
_STRUCTURE_SHELL_ATOM = (
    r"(?:"
    r"\\(?:begin|end)\s*\{\s*[^{}]+\s*\}"
    r"|\\(?:newpage|clearpage)\b"
    r"|<(?:PLACEHOLDER_[^>]+|ENV(?:_BEGIN|_END)?_[^>]+|ITEM_[^>]+|EQROW_[^>]+|EQCOMMENT_[^>]+|INLMATH_[^>]+)>"
    r")"
)
_STRUCTURE_SHELL_PREFIX_RE = re.compile(
    rf"^(?P<shell>(?:\s*{_STRUCTURE_SHELL_ATOM})+\s*)",
    re.DOTALL,
)
_STRUCTURE_SHELL_SUFFIX_RE = re.compile(
    rf"(?P<shell>\s*(?:{_STRUCTURE_SHELL_ATOM}\s*)+)$",
    re.DOTALL,
)
_DOCUMENTCLASS_RE = re.compile(r"\\document(?:class|style)\b")
_PREAMBLE_COMMAND_RE = re.compile(
    r"\\(?:usepackage|RequirePackage|newcommand|renewcommand|providecommand|DeclareMathOperator|def|title|author|date)\b"
)


class LatexParser:
    def __init__(self, dir: str, output_dir: str):
        self.inputs_json = []
        self.envs_json = []
        self.captions_json = []
        self.newcommands_json = []
        self.sections_json = []
        self.dir = dir  # LaTeX project directory
        self.output_dir = output_dir  # Output directory for parsed files
        self.env_count = 0
        self.caption_count = 0

    def parse(self, on_progress: Optional[Callable[[str, int, str], None]] = None):
        """
        Parse the LaTeX document and return the parsed content.
        
        Args:
            on_progress: Optional callback function(stage, percentage, message)
        """
        if on_progress:
            on_progress("parsing", 0, "Starting LaTeX parsing...")
        
        logger.info("Starting LaTeX document parsing")

        main_tex_file = find_main_tex_file(self.dir)
        if not main_tex_file:
            logger.warning("No main tex file found in directory")
            print("⚠️ Warning: There is no main tex file to compile in this directory.")
            return None

        if on_progress:
            on_progress("parsing", 10, "Finding main tex file...")

        main_tex = read_tex_file(main_tex_file)
        if not main_tex:
            logger.warning("Main tex file is empty")
            print("⚠️ Warning: The main tex file is empty.")
            return None
        
        if on_progress:
            on_progress("parsing", 20, "Reading main tex file...")

        main_tex = remove_comments(main_tex)
        full_tex = self._merge_inputs(main_tex)
        full_tex = self._extract_newcommands(full_tex)

        # Delete redundant blank lines to prevent LLM from missing placeholders during translation
        full_tex = compress_newlines(full_tex)

        self._split_to_sections(full_tex)

        # Merge short sections to avoid too many sections
        self._merge_short_sections(min_tokens=50)

        # Chunk overly long sections to prevent LLM catastrophic truncation
        self._chunk_long_sections(max_tokens=4000)

        total_sections = len(self.sections_json)
        if on_progress:
            on_progress("parsing", 80, f"Processing {total_sections} sections...")

        for i, section in enumerate(self.sections_json):
            if on_progress:
                progress = 80 + int(15 * (i / total_sections))
                on_progress("parsing", progress, f"Processing section {i+1}/{total_sections}")

            if section["section"] == "0" or section["section"] == "-1":
                section_content = self._extract_captions(section["content"])
                self.sections_json[i]["trans_content"] = self._extract_envs(section_content)
                self.sections_json[i]["content"] = self.sections_json[i]["trans_content"]
            else:
                section_content = self._extract_captions(section["content"])
                self.sections_json[i]["content"] = self._extract_envs(section_content)

        enc = self._get_token_encoder()
        for i, section in enumerate(self.sections_json):
            self.sections_json[i] = self._annotate_section_chunk(section, enc, max_tokens=4000)

        if on_progress:
            on_progress("parsing", 100, "Parsing complete")
        
        logger.info(f"Parsing complete: {total_sections} sections processed")

    @staticmethod
    def _get_token_encoder():
        try:
            return tiktoken.get_encoding("o200k_base")
        except ValueError:
            return tiktoken.get_encoding("cl100k_base")

    def _merge_inputs(self, tex: str) -> str:
        """
        Merge all the inputs in the main tex file and generate a json file for the inputs.
        """
        main_tex = remove_comments(tex)
        command_name = r'input|include'
        pattern_input = get_command_pattern(command_name)
        pos = 0
        
        while True:
            result = pattern_input.search(main_tex, pos)
            if result is None:
                break
            begin, end = result.span()
            pos = result.end()
            match = result.group(4)
            inputfilepath = os.path.join(self.dir, match)

            if os.path.exists(f'{inputfilepath}'):
                inputfilepath = f'{inputfilepath}'
            elif os.path.exists(f'{inputfilepath}.tex'):
                inputfilepath = f'{inputfilepath}.tex'
            else:
                logger.warning(f"File not found: {inputfilepath}.tex or {inputfilepath}")
                print(f"⚠️ Warning: File not found: {inputfilepath}.tex or {inputfilepath}")
                pos = result.end()
                continue

            input_tex = read_tex_file(inputfilepath)
            input_tex = remove_comments(input_tex)
            input_begin = f"<PLACEHOLDER_{match}_begin>"
            input_end = f"<PLACEHOLDER_{match}_end>"
            input_tex = input_begin + input_tex + input_end
            main_tex = main_tex[:begin] + input_tex + main_tex[end:]
            self.inputs_json.append({
                "command": result.group(0),
                "begin": input_begin,
                "end": input_end,
                "path": match
            })

        return main_tex

    def _extract_envs(self, tex: str) -> str:
        """
        Extract all the environments in the full tex and generate a json file for the environments.
        The environments are replaced with placeholders in the full tex.
        """
        full_tex = remove_comments(tex)
        command_name = r'.*?'
        pattern_env = get_env_pattern(command_name)
        placeholder_pattern_cap = r"<PLACEHOLDER_CAP_\d+>"
        
        no_translate_envs = [
            'equation', 'align', 'align*', 'gather', 'gather*', 'verbatim', 'verbatim*', 'lstlisting*', 'minted', 'minted*',
            'equation*', 'alignat', 'alignat*', 'flalign', 'flalign*', 'split', 'split*', 'cases', 'cases*', 'subequations',
            'figure', 'figure*', 'wrapfigure', 'SCfigure', 'tikzpicture', 'CJK', 'scope',
            'tabularx', 'tabulary', 'longtable*', 'sidewaystable', 'table', 'table*', 'tabular', 'tabular*', 'longtable',
            'multline', 'multline*', 'lstlisting', 'tcolorbox', 'thebibliography', 'bibliography', 'bibitem',
            'algorithm', 'algorithmic', 'algorithmicx', 'algorithm2e', 'algorithmicx*', 'algorithmic*', 'algorithm*',
            'theorem', 'theorem*', 'lemma', 'lemma*', 'proof', 'proof*', 'definition', 'definition*'
        ]
        
        while True:
            result = pattern_env.search(full_tex)
            if result is None:
                break
            self.env_count += 1
            env_name = result.group(1)
            env_content = result.group(0)
            placeholders_cap_in_env = re.findall(placeholder_pattern_cap, env_content)

            need_trans = True

            if env_name in no_translate_envs:
                need_trans = False

            if placeholders_cap_in_env:
                # If there are placeholders in the environment, we usually do not translate it.
                # HOWEVER, for high-level containers like title, author, abstract, frontmatter, keywords,
                # we SHOULD translate them as the TranslatorAgent can handle nested placeholders.
                translatable_containers = ['frontmatter', 'abstract', 'title', 'author', 'keywords']
                if env_name not in translatable_containers:
                    need_trans = False

            placeholder = f"<PLACEHOLDER_ENV_{self.env_count}>"
            full_tex = full_tex.replace(env_content, placeholder, 1)
            self.envs_json.append({
                "placeholder": placeholder,
                "env_name": env_name,
                "content": env_content,
                "trans_content": '',
                "need_trans": need_trans
            })
        
        return full_tex

    def _extract_captions(self, tex: str) -> str:
        """
        Extract all the captions in the full tex and generate a json file for the captions.
        The captions are replaced with placeholders in the full tex.
        """
        full_tex = remove_comments(tex)
        command_name = r'caption|caption\*|subcaption|subcaption\*|title|keywords|abstract|icmltitle|icmltitlerunning'
        pattern_caption = get_command_pattern(command_name)

        while True:
            result = pattern_caption.search(full_tex)
            if result is None:
                break
            self.caption_count += 1
            placeholder = f"<PLACEHOLDER_CAP_{self.caption_count}>"
            full_tex = full_tex.replace(result.group(0), placeholder, 1)
            self.captions_json.append({
                "placeholder": placeholder,
                "cap_type": result.group(1),
                "content": result.group(0),
                "trans_content": ''
            })

        return full_tex
    
    def _extract_newcommands(self, tex: str) -> str:
        """
        Extract all the newcommands in the full tex and generate a json file for the newcommands.
        """
        def get_nonNone(*args):
            result = [arg for arg in args if arg is not None]
            assert len(result) >= 1
            return result[0]
        
        full_tex = remove_comments(tex)
        pattern = get_newcommand_pattern()
        count = 0
        
        while True:
            match = pattern.search(full_tex)
            if match is None:
                break
            
            # Groups 1,2: newcommand name; Group 6: newenvironment name
            name1 = match.group(1)
            name2 = match.group(2)
            env_name = match.group(6)
            name = get_nonNone(name1, name2, env_name)
            
            # Group 3: newcommand args; Group 7: newenvironment args
            n_arguments = match.group(3) or match.group(7)
            
            if n_arguments is None:
                n_arguments = 0
            else:
                n_arguments = int(n_arguments)
            placeholder = f"<PLACEHOLDER_NEWCOMMAND_{count}>"
            full_tex = full_tex.replace(match.group(0), placeholder, 1)
            self.newcommands_json.append({
                "placeholder": placeholder,
                "name": name,
                "content": match.group(0)
            })
            count += 1

        return full_tex
    
    def _split_to_sections(self, tex: str) -> Any:
        """
        Split the full tex to sections and generate a json file for the sections.
        """
        full_tex = remove_comments(tex)
        command_name_section = r'section|subsection|subsubsection|section\*|subsection\*|subsubsection\*'
        pattern_section = get_command_pattern(command_name_section)
        begin_document_pattern = get_begin_document_pattern()
        begin_document_match = begin_document_pattern.search(full_tex)
        preamble = full_tex[:begin_document_match.start()] if begin_document_match else full_tex

        self.sections_json.append({
            "section": "-1",
            "content": preamble,
            "trans_content": preamble
        })

        document = full_tex[begin_document_match.start():] if begin_document_match else full_tex

        section_count = 0
        subsection_count = 0
        subsubsection_count = 0
        first_section_match = pattern_section.search(document)

        if not first_section_match:
            logger.info("No sections found in document")
            print("There is no section in the full tex.")
            self.sections_json.append({
                "section": "0",
                "content": document,
                "trans_content": ''
            })
            return

        before_section = document[:first_section_match.start()] if first_section_match else document
        sections_tex = document[first_section_match.start():] if first_section_match else document
        
        self.sections_json.append({
            "section": "0",
            "content": before_section,
            "trans_content": before_section
        })

        last_pos = 0
        last_result = first_section_match

        for result in pattern_section.finditer(sections_tex):
            if last_pos != result.start():
                if last_result.group(1) == "section" or last_result.group(1) == "section*":
                    section_count += 1
                    subsection_count = 0
                    subsubsection_count = 0
                    self.sections_json.append({
                        "section": f'{section_count}',
                        "content": sections_tex[last_pos:result.start()],
                        "trans_content": ''
                    })
                elif last_result.group(1) == "subsection" or last_result.group(1) == "subsection*":
                    subsection_count += 1
                    subsubsection_count = 0
                    self.sections_json.append({
                        "section": f'{section_count}_{subsection_count}',
                        "content": sections_tex[last_pos:result.start()],
                        "trans_content": ''
                    })
                elif last_result.group(1) == "subsubsection" or last_result.group(1) == "subsubsection*":
                    subsubsection_count += 1
                    self.sections_json.append({
                        "section": f'{section_count}_{subsection_count}_{subsubsection_count}',
                        "content": sections_tex[last_pos:result.start()],
                        "trans_content": ''
                    })
            last_pos = result.start()
            last_result = result

        if last_result.group(1) == "section" or last_result.group(1) == "section*":
            section_count += 1
            subsection_count = 0
            subsubsection_count = 0
            self.sections_json.append({
                "section": f'{section_count}',
                "content": sections_tex[last_pos:],
                "trans_content": ''
            })
        elif last_result.group(1) == "subsection" or last_result.group(1) == "subsection*":
            subsection_count += 1
            subsubsection_count = 0
            self.sections_json.append({
                "section": f'{section_count}_{subsection_count}',
                "content": sections_tex[last_pos:],
                "trans_content": ''
            })
        elif last_result.group(1) == "subsubsection" or last_result.group(1) == "subsubsection*":
            subsubsection_count += 1
            self.sections_json.append({
                "section": f'{section_count}_{subsection_count}_{subsubsection_count}',
                "content": sections_tex[last_pos:],
                "trans_content": ''
            })

    def _merge_short_sections(self, min_tokens=20):
        """
        Merge sections that are too short to save the number of API requests
        """
        try:
            enc = tiktoken.get_encoding("o200k_base")
        except ValueError:
            enc = tiktoken.get_encoding("cl100k_base")
        merged_sections = []
        i = 0
        sections = self.sections_json

        while i < len(sections):
            combined_content = sections[i]["content"]
            combined_section_ids = [sections[i]["section"]]
            total_tokens = len(enc.encode(combined_content))
            start_section = sections[i]
            j = i + 1

            while total_tokens < min_tokens and j < len(sections):
                combined_content += "\n" + sections[j]["content"]
                combined_section_ids.append(sections[j]["section"])
                total_tokens = len(enc.encode(combined_content))
                j += 1

            if total_tokens < min_tokens and len(merged_sections) > 0:
                merged_sections[-1]["content"] += "\n" + combined_content
                merged_sections[-1]["section"] += "+" + "+".join(combined_section_ids)
                logger.debug(f"Merged sections: {merged_sections[-1]['section']}")
                print(merged_sections[-1]["section"])
            else:
                merged_section = start_section.copy()
                merged_section["content"] = combined_content
                merged_section["section"] = "+".join(combined_section_ids)
                merged_sections.append(merged_section)

            i = j

        self.sections_json = merged_sections

    def _chunk_long_sections(self, max_tokens=4000):
        """
        Split sections that exceed max_tokens into smaller sub-chunks based on natural boundaries
        (paragraphs first, then sentences) to prevent LLM truncation.
        Tracks previous_context to maintain semantic continuity across LLM calls.
        Marks chunks that still exceed `max_tokens` after boundary search as
        `oversize_no_safe_boundary=True` for deterministic source-pass-through gating.

        Structure-Aware Split Invariant (OpenSpec: structure-aware-chunking):
        Before finalizing a split point, we verify via `_is_safe_split_boundary`
        that the current chunk ends at brace depth 0 and outside any \\begin...\\end
        environment. If the boundary is unsafe, we defer the split and accumulate
        more text, ultimately flagging the overall chunk as oversize_no_safe_boundary.
        """
        try:
            enc = tiktoken.get_encoding("o200k_base")
        except ValueError:
            enc = tiktoken.get_encoding("cl100k_base")
        chunked_sections = []
        
        for section in self.sections_json:
            content = section["content"]
            tokens = len(enc.encode(content))
            
            if tokens <= max_tokens:
                self._annotate_section_chunk(section, enc, max_tokens)
                chunked_sections.append(section)
                continue
                
            logger.info(f"Section {section['section']} exceeds {max_tokens} tokens ({tokens} tokens). Splitting...")
            
            # 1. Try splitting by paragraph (double newline)
            parts = re.split(r'(\n{2,})', content)
            paragraphs = []
            current_p = ""
            for part in parts:
                if re.match(r'\n{2,}', part):
                    current_p += part
                    paragraphs.append(current_p)
                    current_p = ""
                else:
                    current_p += part
            if current_p:
                paragraphs.append(current_p)
                
            # If a single paragraph is still too large, split by sentence boundary
            refined_parts = []
            for p in paragraphs:
                if len(enc.encode(p)) > max_tokens:
                    # Split by sentence boundary '. ', but preserve the delimiter
                    sentences = re.split(r'(\.\s+)', p)
                    current_s = ""
                    for s in sentences:
                        if re.match(r'\.\s+', s):
                            current_s += s
                            refined_parts.append(current_s)
                            current_s = ""
                        else:
                            current_s += s
                    if current_s:
                        refined_parts.append(current_s)
                else:
                    refined_parts.append(p)

            # Assemble sub-chunks — only split at brace-depth-zero boundaries
            current_chunk = ""
            current_chunk_tokens = 0
            sub_chunk_idx = 1
            previous_context = ""
            
            for part in refined_parts:
                part_tokens = len(enc.encode(part))
                
                # If adding this part exceeds max, check whether the
                # boundary before `part` is a safe split point (brace depth == 0
                # and not inside a \begin...\end environment).
                if current_chunk and (current_chunk_tokens + part_tokens > max_tokens):
                    if self._is_safe_split_boundary(current_chunk):
                        new_section = section.copy()
                        new_section["section"] = f"{section['section']}_chunk_{sub_chunk_idx}"
                        new_section["content"] = current_chunk
                        if previous_context:
                            new_section["previous_context"] = previous_context
                        chunk_tokens = len(enc.encode(current_chunk))
                        new_section["chunk_token_count"] = chunk_tokens
                        if chunk_tokens > max_tokens:
                            new_section["oversize_no_safe_boundary"] = True
                        self._annotate_section_chunk(new_section, enc, max_tokens)
                        chunked_sections.append(new_section)
                        sub_chunk_idx += 1
                        
                        # Store trailing text of the completed chunk as context
                        tail = current_chunk[-1000:]
                        last_paragraph_match = re.search(r'([^\n]+)$', tail)
                        if last_paragraph_match:
                            previous_context = last_paragraph_match.group(1).strip()
                        else:
                            previous_context = tail.strip()
                            
                        current_chunk = ""
                        current_chunk_tokens = 0
                    else:
                        # Not a safe boundary — accumulate and defer the split decision.
                        logger.debug(
                            f"Section {section['section']}: skipping split at unsafe boundary "
                            f"(brace depth > 0 or inside environment). Accumulating."
                        )
                    
                current_chunk += part
                current_chunk_tokens += part_tokens
                
            # Final remaining chunk
            if current_chunk:
                new_section = section.copy()
                new_section["section"] = f"{section['section']}_chunk_{sub_chunk_idx}"
                new_section["content"] = current_chunk
                if previous_context:
                    new_section["previous_context"] = previous_context
                chunk_tokens = len(enc.encode(current_chunk))
                new_section["chunk_token_count"] = chunk_tokens
                if chunk_tokens > max_tokens:
                    new_section["oversize_no_safe_boundary"] = True
                self._annotate_section_chunk(new_section, enc, max_tokens)
                chunked_sections.append(new_section)

        self.sections_json = self._collapse_placeholder_only_chunks(chunked_sections, enc, max_tokens)

    @staticmethod
    def _base_section_id(section_id: str) -> str:
        if not section_id:
            return ""
        match = _SECTION_CHUNK_ID_RE.match(section_id)
        if match:
            return match.group("base")
        return section_id

    @staticmethod
    def _strip_structural_shell(text: str) -> str:
        stripped = _PLACEHOLDER_ATOM_RE.sub(" ", text or "")
        stripped = _LATEX_COMMAND_TOKEN_RE.sub(" ", stripped)
        stripped = _STRUCTURAL_SYMBOL_RE.sub(" ", stripped)
        stripped = re.sub(r"\s+", " ", stripped)
        return stripped.strip()

    @staticmethod
    def _extract_structure_shells(content: str) -> Dict[str, Any]:
        text = content or ""
        leading_shell = ""
        trailing_shell = ""
        core_content = text

        leading_match = _STRUCTURE_SHELL_PREFIX_RE.match(core_content)
        if leading_match:
            leading_shell = leading_match.group("shell")
            core_content = core_content[leading_match.end():]

        trailing_match = _STRUCTURE_SHELL_SUFFIX_RE.search(core_content)
        if trailing_match:
            trailing_shell = trailing_match.group("shell")
            core_content = core_content[:trailing_match.start()]

        contains_structure_shell = bool(leading_shell or trailing_shell)
        structure_shell_only = contains_structure_shell and not core_content.strip()
        return {
            "leading_structure_shell": leading_shell,
            "core_translatable_content": core_content if contains_structure_shell else text,
            "trailing_structure_shell": trailing_shell,
            "contains_structure_shell": contains_structure_shell,
            "structure_shell_only": structure_shell_only,
        }

    def _annotate_structure_shells(self, section: Dict[str, Any]) -> Dict[str, Any]:
        section.update(self._extract_structure_shells(section.get("content", "") or ""))
        return section

    def _annotate_section_chunk(self, section: Dict[str, Any], enc: Any, max_tokens: int) -> Dict[str, Any]:
        content = section.get("content", "") or ""
        self._annotate_structure_shells(section)
        stripped = self._strip_structural_shell(section.get("core_translatable_content", content))
        placeholder_only = bool(content.strip()) and _PLACEHOLDER_ATOM_RE.sub("", content).strip() == ""
        translatable_char_count = len(re.findall(r"[A-Za-z\u00C0-\u024F\u4e00-\u9fff]", stripped))
        base_section_id = self._base_section_id(str(section.get("section", "")))

        chunk_kind = "normal"
        if placeholder_only:
            chunk_kind = "placeholder_only"
        elif translatable_char_count == 0:
            chunk_kind = "low_text_density"
        elif section.get("oversize_no_safe_boundary"):
            chunk_kind = "oversize"

        chunk_role = "normal"
        if (
            base_section_id == "-1"
            or _DOCUMENTCLASS_RE.search(content)
            or (
                "\\begin{document}" not in content
                and _PREAMBLE_COMMAND_RE.search(content)
                and not re.search(r"\\(?:section|subsection|subsubsection|paragraph|chapter)\*?\{", content)
            )
        ):
            chunk_role = "document_root"
        elif section.get("contains_structure_shell"):
            chunk_role = "section_with_structure_shell"

        immutable_only = chunk_kind in {"placeholder_only", "low_text_density"} and translatable_char_count == 0
        if section.get("structure_shell_only"):
            immutable_only = True

        section["chunk_token_count"] = int(section.get("chunk_token_count") or len(enc.encode(content)))
        section["chunk_kind"] = chunk_kind
        section["chunk_role"] = chunk_role
        section["immutable_only"] = bool(immutable_only)
        section["translatable_char_count"] = int(translatable_char_count)

        if immutable_only:
            section["trans_content"] = content
            section["translation_status"] = "immutable_passthrough"

        return section

    def _collapse_placeholder_only_chunks(
        self,
        sections: List[Dict[str, Any]],
        enc: Any,
        max_tokens: int,
    ) -> List[Dict[str, Any]]:
        collapsed: List[Dict[str, Any]] = []
        deferred_prefix = ""
        deferred_base = ""

        for section in sections:
            current = self._annotate_section_chunk(section, enc, max_tokens)
            current_section_id = str(current.get("section", ""))
            current_base = self._base_section_id(current_section_id)

            if current.get("chunk_kind") == "placeholder_only" and "_chunk_" in current_section_id:
                if collapsed and self._base_section_id(str(collapsed[-1].get("section", ""))) == current_base:
                    collapsed[-1]["content"] = (collapsed[-1].get("content", "") or "") + current.get("content", "")
                    collapsed[-1].pop("trans_content", None)
                    self._annotate_section_chunk(collapsed[-1], enc, max_tokens)
                    if collapsed[-1]["chunk_token_count"] > max_tokens:
                        collapsed[-1]["oversize_no_safe_boundary"] = True
                        collapsed[-1]["chunk_kind"] = "oversize"
                    continue

                deferred_prefix += current.get("content", "")
                deferred_base = current_base
                continue

            if deferred_prefix and deferred_base == current_base:
                current["content"] = deferred_prefix + (current.get("content", "") or "")
                current.pop("trans_content", None)
                self._annotate_section_chunk(current, enc, max_tokens)
                if current["chunk_token_count"] > max_tokens:
                    current["oversize_no_safe_boundary"] = True
                    if current["chunk_kind"] == "normal":
                        current["chunk_kind"] = "oversize"
                deferred_prefix = ""
                deferred_base = ""

            collapsed.append(current)

        if deferred_prefix:
            if collapsed and self._base_section_id(str(collapsed[-1].get("section", ""))) == deferred_base:
                collapsed[-1]["content"] = (collapsed[-1].get("content", "") or "") + deferred_prefix
                collapsed[-1].pop("trans_content", None)
                self._annotate_section_chunk(collapsed[-1], enc, max_tokens)
                if collapsed[-1]["chunk_token_count"] > max_tokens:
                    collapsed[-1]["oversize_no_safe_boundary"] = True
                    if collapsed[-1]["chunk_kind"] == "normal":
                        collapsed[-1]["chunk_kind"] = "oversize"
            else:
                orphan_chunk = {
                    "section": f"{deferred_base}_chunk_orphan" if deferred_base else "orphan_chunk",
                    "content": deferred_prefix,
                    "trans_content": deferred_prefix,
                }
                self._annotate_section_chunk(orphan_chunk, enc, max_tokens)
                collapsed.append(orphan_chunk)

        return collapsed

    @staticmethod
    def _is_safe_split_boundary(text: str) -> bool:
        """
        Return True iff the end of `text` is a safe LaTeX split boundary:
        - The brace depth (counting { vs }) must be 0.
        - We must not be inside any \\begin{...}...\\end{...} environment.

        This ensures we never split \\textbf{long text} mid-brace or separate
        a \\begin from its matching \\end.
        """
        depth = 0
        env_stack = []  # stack of environment names currently open

        i = 0
        while i < len(text):
            ch = text[i]

            if ch == '\\':
                # Look for \begin{name} and \end{name}
                begin_m = re.match(r'\\begin\s*\{([^}]*)\}', text[i:])
                if begin_m:
                    env_stack.append(begin_m.group(1))
                    i += begin_m.end()
                    continue

                end_m = re.match(r'\\end\s*\{([^}]*)\}', text[i:])
                if end_m:
                    env_name = end_m.group(1)
                    if env_stack and env_stack[-1] == env_name:
                        env_stack.pop()
                    i += end_m.end()
                    continue

                i += 1
            elif ch == '{':
                depth += 1
                i += 1
            elif ch == '}':
                depth -= 1
                i += 1
            else:
                i += 1

        return depth == 0 and len(env_stack) == 0

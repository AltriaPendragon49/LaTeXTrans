"""
Generator Agent

Adapted from prototype system with:
- All Streamlit dependencies removed
- Integrated new compile_with_fallback() function
- Progress callback mechanism added
- Python logging integrated
"""

from typing import Dict, Any, Optional, Callable
from .base_tool_agent import BaseToolAgent
from backend.app.services.latex.reconstruct import LatexConstructor
from backend.app.services.latex.compiler import compile_with_intelligent_fallback, find_main_tex_file
from backend.app.services.latex.utils import apply_formatting_config
from pathlib import Path
import os
import shutil
import logging

logger = logging.getLogger(__name__)


class GeneratorAgent(BaseToolAgent):
    def __init__(self, 
                 config: Dict[str, Any],
                 project_dir: str = None,
                 output_dir: str = None,
                 on_progress: Optional[Callable[[str, int, str], None]] = None
                 ):
        super().__init__(agent_name="GeneratorAgent", config=config, on_progress=on_progress)
        self.config = config
        self.project_dir = project_dir
        self.output_dir = output_dir
        self.latex_engine = config.get("latex_engine", "auto")

    def execute(self) -> Optional[str]:
        """
        Execute generation task: reconstruct LaTeX and compile to PDF
        
        Returns:
            Path to generated PDF file, or None if compilation failed
        """
        self.log(f"Starting generation for project: {os.path.basename(self.project_dir)}")
        self.update_progress(5, "Starting generation")

        self.update_progress(10, "Reading JSON maps")
        sections = self.read_file(Path(self.output_dir, "sections_map.json"), "json")
        self.update_progress(20, "Loading sections")
        
        captions = self.read_file(Path(self.output_dir, "captions_map.json"), "json")
        self.update_progress(30, "Loading captions")
        
        envs = self.read_file(Path(self.output_dir, "envs_map.json"), "json")
        self.update_progress(40, "Loading environments")
        
        newcommands = self.read_file(Path(self.output_dir, "newcommands_map.json"), "json")
        self.update_progress(50, "Loading newcommands")
        
        inputs = self.read_file(Path(self.output_dir, "inputs_map.json"), "json")
        self.update_progress(60, "Loading inputs")

        self.update_progress(65, "Creating translation project directory")
        transed_latex_dir = self._create_transed_latex_folder(self.project_dir)
        self.log(f"Created translation directory: {transed_latex_dir}")

        self.update_progress(70, "Reconstructing LaTeX document")
        target_language = self.config.get("target_language", "en")
        latex_constructor = LatexConstructor(
            sections=sections,
            captions=captions,
            envs=envs,
            inputs=inputs,
            newcommands=newcommands,
            output_latex_dir=transed_latex_dir,
            target_language=target_language
        )
        latex_constructor.construct(on_progress=self.on_progress)

        self.update_progress(80, "Applying formatting config")
        
        # Apply typography formatting config to main .tex file (if specified)
        formatting_config = self.config.get("formatting")
        if formatting_config:
            transed_main_tex = find_main_tex_file(transed_latex_dir)
            if transed_main_tex:
                try:
                    with open(transed_main_tex, 'r', encoding='utf-8', errors='replace') as f:
                        tex_content = f.read()
                    tex_content, fmt_warnings = apply_formatting_config(tex_content, formatting_config)
                    with open(transed_main_tex, 'w', encoding='utf-8') as f:
                        f.write(tex_content)
                    logger.info(f"Applied formatting config to {transed_main_tex}")
                    # Surface any auto-downgrade warnings via progress callback
                    for warn in fmt_warnings:
                        logger.warning(f"[FormattingConfig] {warn}")
                        self.update_progress(80, f"⚠ 排版提示：{warn}")
                    # Store warnings for caller to forward to task_manager
                    if fmt_warnings and not hasattr(self, '_fmt_warnings'):
                        self._fmt_warnings = []
                    if fmt_warnings:
                        self._fmt_warnings.extend(fmt_warnings)
                except Exception as e:
                    logger.warning(f"Failed to apply formatting config: {e}")
            else:
                logger.warning("No main .tex file found; formatting config not applied")

        self.update_progress(80, "Compiling PDF document")
        
        # Use intelligent main tex file detection
        main_tex = find_main_tex_file(transed_latex_dir)
        
        if not main_tex:
            logger.error(f"No main .tex file found in {transed_latex_dir}")
            self.update_progress(100, "No main .tex file found")
            return None
        
        logger.info(f"Compiling {Path(main_tex).name}...")
        
        # Build engine order based on user configuration
        preferred_order = None
        if self.latex_engine and self.latex_engine != "auto":
            # User selected specific engine - prioritize it
            all_engines = ["pdflatex", "xelatex", "lualatex"]
            if self.latex_engine in all_engines:
                all_engines.remove(self.latex_engine)
                preferred_order = [self.latex_engine] + all_engines
                logger.info(f"Using user-specified engine order: {preferred_order}")
        
        # Use new intelligent compiler with fallback
        result = compile_with_intelligent_fallback(
            tex_file=str(main_tex),
            output_dir=transed_latex_dir,
            preferred_order=preferred_order
        )

        pdf_file = result.get("pdf_path")
        
        if pdf_file:
            self.update_progress(100, "PDF generation complete")
            self.log(f"Successfully generated PDF: {pdf_file}")
            return pdf_file
        else:
            self.update_progress(100, "PDF compilation failed")
            self.log("Failed to compile PDF document", level="error")
            if result.get("errors"):
                self.log(f"Errors: {result['errors']}", level="error")
            return None
        
    def _create_transed_latex_folder(self, src_dir: str) -> str:
        """
        Create a translated folder by copying the source directory.
        
        Args:
            src_dir: Source LaTeX project directory
            
        Returns:
            Path to created translation directory
        """
        if not os.path.isdir(src_dir):
            raise NotADirectoryError(f"The path {src_dir} is not a valid directory.")

        base_name = os.path.basename(src_dir)
        dest_dir = os.path.join(self.output_dir, base_name)

        if os.path.exists(dest_dir):
            self.log(f"Removing existing directory: {dest_dir}", level="debug")
            shutil.rmtree(dest_dir)
        
        shutil.copytree(src_dir, dest_dir)
        self.log(f"Copied {src_dir} to {dest_dir}", level="debug")

        return dest_dir

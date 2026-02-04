"""
LaTeX Directory Validator Service

Validates uploaded directories to ensure they contain valid LaTeX projects.
Detects main entry files and provides warnings/errors for common issues.
"""

import re
import logging
from pathlib import Path
from typing import Optional

from backend.app.models.config_models import LatexValidation

logger = logging.getLogger(__name__)


def validate_latex_directory(path: Path) -> LatexValidation:
    """
    Validate a directory to check if it's a valid LaTeX project.
    
    Detection logic:
    1. Search for .tex files recursively
    2. Identify main entry file by:
       - Filename: main.tex, paper.tex, article.tex, document.tex
       - Content: Contains \\documentclass
    3. Return validation result with warnings and errors
    
    Args:
        path: Path to the directory to validate
    
    Returns:
        LatexValidation with validation results
    """
    logger.info(f"Validating LaTeX directory: {path}")
    
    warnings = []
    errors = []
    main_file = None
    
    if not path.exists():
        return LatexValidation(
            is_valid=False,
            errors=["目录不存在"]
        )
    
    if not path.is_dir():
        return LatexValidation(
            is_valid=False,
            errors=["路径不是有效目录"]
        )
    
    # Find all .tex files
    tex_files = list(path.rglob("*.tex"))
    tex_file_paths = [str(f.relative_to(path)) for f in tex_files]
    
    if not tex_files:
        return LatexValidation(
            is_valid=False,
            tex_files=[],
            errors=["压缩包中无 .tex 文件"]
        )
    
    logger.info(f"Found {len(tex_files)} .tex files")
    
    # Priority names for main file detection
    priority_names = ["main.tex", "paper.tex", "article.tex", "document.tex"]
    
    # Try to find main file by priority names
    for priority_name in priority_names:
        for tex_file in tex_files:
            if tex_file.name.lower() == priority_name:
                main_file = str(tex_file.relative_to(path))
                logger.info(f"Found main file by name: {main_file}")
                break
        if main_file:
            break
    
    # If not found by name, search for \documentclass in file content
    if not main_file:
        candidates = []
        for tex_file in tex_files:
            try:
                content = tex_file.read_text(encoding='utf-8', errors='ignore')
                # Match \documentclass with optional parameters
                if re.search(r'\\documentclass(\[.*?\])?\{', content):
                    candidates.append(str(tex_file.relative_to(path)))
            except Exception as e:
                logger.warning(f"Error reading {tex_file}: {e}")
        
        if len(candidates) == 1:
            main_file = candidates[0]
            logger.info(f"Found main file by \\documentclass: {main_file}")
        elif len(candidates) > 1:
            # Multiple candidates, use the first one and warn
            main_file = candidates[0]
            warnings.append(
                f"Multiple files contain \\documentclass: {', '.join(candidates)}. "
                f"Using {main_file} as main file."
            )
            logger.warning(f"Multiple main file candidates: {candidates}")
    
    # If still not found, use the first .tex file
    if not main_file:
        main_file = str(tex_files[0].relative_to(path))
        warnings.append(
            f"Could not detect main entry file. Using first .tex file: {main_file}"
        )
        logger.warning(f"Using first .tex file as main: {main_file}")
    
    # Check for common issues
    # 1. Check if there are too many .tex files (might indicate nested projects)
    if len(tex_files) > 50:
        warnings.append(
            f"Directory contains {len(tex_files)} .tex files. "
            "This might slow down translation."
        )
    
    # 2. Check for missing common files
    has_bib = any(path.rglob("*.bib"))
    if not has_bib:
        # Not an error, just informational
        pass
    
    is_valid = len(errors) == 0
    
    logger.info(f"Validation result: valid={is_valid}, main_file={main_file}")
    
    return LatexValidation(
        is_valid=is_valid,
        main_file=main_file,
        tex_files=tex_file_paths,
        warnings=warnings,
        errors=errors
    )


def find_main_tex_file(path: Path) -> Optional[Path]:
    """
    Convenience function to find the main .tex file in a directory.
    
    Args:
        path: Path to the LaTeX project directory
    
    Returns:
        Path to the main .tex file, or None if not found/invalid
    """
    validation = validate_latex_directory(path)
    if validation.is_valid and validation.main_file:
        return path / validation.main_file
    return None

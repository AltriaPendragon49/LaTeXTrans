"""
Intelligent LaTeX Compiler with Fallback

Implements multi-stage compilation strategy:
1. Try pdflatex first
2. If fails or has errors, try xelatex
3. Compare error counts from .log files
4. Select PDF with fewer errors or return best available
"""

import os
import re
import subprocess
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple, List

logger = logging.getLogger(__name__)


class CompilationResult:
    """Result of a compilation attempt"""
    
    def __init__(
        self,
        success: bool,
        pdf_path: Optional[str] = None,
        log_path: Optional[str] = None,
        error_count: int = 0,
        errors: Optional[List[str]] = None,
        exit_code: int = 0
    ):
        self.success = success
        self.pdf_path = pdf_path
        self.log_path = log_path
        self.error_count = error_count
        self.errors = errors or []
        self.exit_code = exit_code


def parse_log_errors(log_path: str) -> Tuple[int, List[str]]:
    """
    Parse LaTeX .log file and count errors
    
    Matches patterns:
    - ! LaTeX Error
    - ! Undefined control sequence
    - ! Missing
    
    Args:
        log_path: Path to .log file
    
    Returns:
        Tuple of (error_count, error_lines)
    """
    if not os.path.exists(log_path):
        return 0, []
    
    error_patterns = [
        r'^! LaTeX Error',
        r'^! Undefined control sequence',
        r'^! Missing',
        r'^! .*Error',
    ]
    
    errors = []
    
    try:
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                for pattern in error_patterns:
                    if re.match(pattern, line):
                        errors.append(line)
                        break
    except Exception as e:
        logger.warning(f"Failed to parse log file {log_path}: {e}")
        return 0, []
    
    return len(errors), errors


def compile_latex(
    tex_file: str,
    output_dir: str,
    engine: str = "pdflatex",
    max_runs: int = 2
) -> CompilationResult:
    """
    Compile LaTeX file with specified engine
    
    Args:
        tex_file: Path to .tex file
        output_dir: Output directory
        engine: LaTeX engine ("pdflatex" or "xelatex")
        max_runs: Maximum compilation runs (for references)
    
    Returns:
        CompilationResult object
    """
    if not os.path.exists(tex_file):
        logger.error(f"TeX file not found: {tex_file}")
        return CompilationResult(success=False, exit_code=-1)
    
    tex_path = Path(tex_file)
    tex_filename = tex_path.name
    tex_basename = tex_path.stem
    
    # Prepare output directory
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Compiling {tex_filename} with {engine}...")
    
    # Run compilation (may need multiple runs for references)
    last_exit_code = 0
    for run in range(max_runs):
        try:
            # -interaction=nonstopmode: continue on errors
            # -halt-on-error: stop on first error (we use nonstopmode instead)
            # -output-directory: specify output directory
            cmd = [
                engine,
                "-interaction=nonstopmode",
                "-output-directory", str(output_dir),
                tex_filename
            ]
            
            result = subprocess.run(
                cmd,
                cwd=str(tex_path.parent),
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            last_exit_code = result.returncode
            
            logger.info(f"{engine} run {run + 1}/{max_runs} completed with exit code {result.returncode}")
            
        except subprocess.TimeoutExpired:
            logger.error(f"{engine} compilation timed out")
            return CompilationResult(success=False, exit_code=-2)
        except Exception as e:
            logger.error(f"{engine} compilation failed: {e}")
            return CompilationResult(success=False, exit_code=-3)
    
    # Check for output PDF
    pdf_path = out_path / f"{tex_basename}.pdf"
    log_path = out_path / f"{tex_basename}.log"
    
    pdf_exists = pdf_path.exists()
    
    # Parse errors from log file
    error_count = 0
    errors = []
    if log_path.exists():
        error_count, errors = parse_log_errors(str(log_path))
    
    success = pdf_exists and error_count == 0
    
    logger.info(
        f"{engine} compilation result: "
        f"PDF={'✓' if pdf_exists else '✗'}, "
        f"Errors={error_count}, "
        f"Exit Code={last_exit_code}"
    )
    
    return CompilationResult(
        success=success,
        pdf_path=str(pdf_path) if pdf_exists else None,
        log_path=str(log_path) if log_path.exists() else None,
        error_count=error_count,
        errors=errors,
        exit_code=last_exit_code
    )


def compile_with_fallback(tex_file: str, output_dir: str) -> Dict:
    """
    Intelligent LaTeX compilation with fallback strategy
    
    Strategy:
    1. Try pdflatex first
    2. If perfect (zero errors), return immediately
    3. If failed or has errors, try xelatex
    4. Compare error counts and select best PDF
    5. If both fail to produce PDF, raise exception
    
    Args:
        tex_file: Path to .tex file
        output_dir: Output directory
    
    Returns:
        Dictionary with:
        - pdf_path: Path to best PDF
        - status: "completed" | "completed_with_warnings" | "failed_compilation"
        - engine: Engine that produced the PDF
        - error_count: Number of errors in selected PDF
        - warnings: Warning message if errors present
        - errors: Combined error details if compilation failed
    
    Raises:
        Exception: If both compilers fail to produce any PDF
    """
    logger.info(f"Starting intelligent compilation for {tex_file}")
    
    # Step 1: Try pdflatex
    pdflatex_result = compile_latex(tex_file, output_dir, engine="pdflatex")
    
    # Perfect compilation - return immediately
    if pdflatex_result.success and pdflatex_result.error_count == 0:
        logger.info("✅ pdflatex produced perfect compilation (zero errors)")
        return {
            "pdf_path": pdflatex_result.pdf_path,
            "status": "completed",
            "engine": "pdflatex",
            "error_count": 0,
            "warnings": None,
            "errors": None
        }
    
    # Step 2: Try xelatex fallback
    logger.info("⚡ Attempting xelatex fallback...")
    xelatex_result = compile_latex(tex_file, output_dir, engine="xelatex")
    
    # Perfect xelatex compilation
    if xelatex_result.success and xelatex_result.error_count == 0:
        logger.info("✅ xelatex produced perfect compilation (zero errors)")
        return {
            "pdf_path": xelatex_result.pdf_path,
            "status": "completed",
            "engine": "xelatex",
            "error_count": 0,
            "warnings": None,
            "errors": None
        }
    
    # Step 3: Compare results and select best
    pdflatex_has_pdf = pdflatex_result.pdf_path is not None
    xelatex_has_pdf = xelatex_result.pdf_path is not None
    
    # Case 1: Only pdflatex produced PDF
    if pdflatex_has_pdf and not xelatex_has_pdf:
        logger.warning(f"⚠️ Only pdflatex produced PDF (with {pdflatex_result.error_count} errors)")
        return {
            "pdf_path": pdflatex_result.pdf_path,
            "status": "completed_with_warnings",
            "engine": "pdflatex",
            "error_count": pdflatex_result.error_count,
            "warnings": f"Compilation completed with {pdflatex_result.error_count} errors. xelatex failed to produce output.",
            "errors": None
        }
    
    # Case 2: Only xelatex produced PDF
    if xelatex_has_pdf and not pdflatex_has_pdf:
        logger.warning(f"⚠️ Only xelatex produced PDF (with {xelatex_result.error_count} errors)")
        return {
            "pdf_path": xelatex_result.pdf_path,
            "status": "completed_with_warnings",
            "engine": "xelatex",
            "error_count": xelatex_result.error_count,
            "warnings": f"Compilation completed with {xelatex_result.error_count} errors. pdflatex failed to produce output.",
            "errors": None
        }
    
    # Case 3: Both produced PDFs - select one with fewer errors
    if pdflatex_has_pdf and xelatex_has_pdf:
        if pdflatex_result.error_count <= xelatex_result.error_count:
            engine = "pdflatex"
            result = pdflatex_result
        else:
            engine = "xelatex"
            result = xelatex_result
        
        logger.warning(
            f"⚠️ Selected {engine} PDF with {result.error_count} errors "
            f"(pdflatex: {pdflatex_result.error_count}, xelatex: {xelatex_result.error_count})"
        )
        
        return {
            "pdf_path": result.pdf_path,
            "status": "completed_with_warnings",
            "engine": engine,
            "error_count": result.error_count,
            "warnings": f"Compilation completed with {result.error_count} errors using {engine}.",
            "errors": None
        }
    
    # Case 4: Both failed to produce PDF
    logger.error("❌ Both pdflatex and xelatex failed to produce PDF")
    
    # Combine error messages
    combined_errors = "Compilation failed with both engines:\n\n"
    combined_errors += f"pdflatex ({pdflatex_result.error_count} errors):\n"
    combined_errors += "\n".join(pdflatex_result.errors[:10])  # First 10 errors
    combined_errors += f"\n\nxelatex ({xelatex_result.error_count} errors):\n"
    combined_errors += "\n".join(xelatex_result.errors[:10])
    
    return {
        "pdf_path": None,
        "status": "failed_compilation",
        "engine": None,
        "error_count": pdflatex_result.error_count + xelatex_result.error_count,
        "warnings": None,
        "errors": combined_errors
    }


class LaTeXCompiler:
    """
    LaTeX Compiler wrapper for backward compatibility with prototype system
    """
    
    def __init__(self, output_latex_dir: str):
        self.output_latex_dir = output_latex_dir
    
    def compile(self) -> Optional[str]:
        """
        Compile LaTeX document in the output directory
        
        Returns:
            Path to PDF file or None if compilation failed
        """
        # Find main .tex file
        tex_files = list(Path(self.output_latex_dir).glob("*.tex"))
        
        if not tex_files:
            logger.error(f"No .tex files found in {self.output_latex_dir}")
            return None
        
        # Try to find main.tex or the first .tex file
        main_tex = None
        for tex in tex_files:
            if tex.stem.lower() in ["main", "paper", "article"]:
                main_tex = tex
                break
        
        if main_tex is None:
            main_tex = tex_files[0]
        
        logger.info(f"Compiling {main_tex.name}...")
        
        try:
            result = compile_with_fallback(str(main_tex), self.output_latex_dir)
            
            if result["pdf_path"]:
                logger.info(f"✅ Compilation succeeded: {result['pdf_path']}")
                return result["pdf_path"]
            else:
                logger.error(f"❌ Compilation failed: {result.get('errors', 'Unknown error')}")
                raise Exception(result.get("errors", "Compilation failed"))
        
        except Exception as e:
            logger.error(f"Compilation error: {e}")
            raise

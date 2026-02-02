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
import json
from pathlib import Path
from typing import Dict, Optional, Tuple, List

logger = logging.getLogger(__name__)

# CJK character detection threshold
CJK_THRESHOLD = 100

# Maximum content to read for language detection (100KB)
MAX_DETECTION_CONTENT = 100 * 1024


def detect_document_language_from_content(content: str) -> str:
    """
    Detect document language from text content.
    
    Checks for CJK (Chinese, Japanese, Korean) characters.
    
    Args:
        content: Text content to analyze
        
    Returns:
        "cjk" if CJK characters exceed threshold, otherwise "latin"
    """
    import re
    
    # CJK character ranges:
    # - Chinese: \u4e00-\u9fff (CJK Unified Ideographs)
    # - Japanese Hiragana: \u3040-\u309f
    # - Japanese Katakana: \u30a0-\u30ff  
    # - Korean Hangul: \uac00-\ud7af
    cjk_pattern = re.compile(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]')
    
    cjk_chars = cjk_pattern.findall(content)
    cjk_count = len(cjk_chars)
    
    if cjk_count > CJK_THRESHOLD:
        return "cjk"
    return "latin"


def detect_document_language(tex_file: str) -> str:
    """
    Detect the primary language type of a LaTeX document.
    
    Strategy:
    1. Read the .tex file content (up to 100KB)
    2. Count CJK characters (Chinese, Japanese, Korean)
    3. If CJK chars exceed threshold (100), classify as CJK document
    
    Args:
        tex_file: Path to .tex file
        
    Returns:
        "cjk" or "latin"
    """
    try:
        with open(tex_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(MAX_DETECTION_CONTENT)
        return detect_document_language_from_content(content)
    except Exception as e:
        logger.warning(f"Failed to detect language for {tex_file}: {e}")
        return "latin"  # Default to latin for safety


def verify_pdf_ready(pdf_path: str, timeout: float = 5.0) -> bool:
    """
    Verify that a PDF file is fully ready for use.
    
    Checks:
    1. File exists
    2. File size > 0
    3. File is readable (can be opened)
    4. File has valid PDF header (%PDF-)
    5. Wait for file system buffer to flush
    
    Args:
        pdf_path: Path to PDF file
        timeout: Maximum wait time in seconds
        
    Returns:
        True if PDF is ready, False otherwise
    """
    import time
    start_time = time.time()
    
    while (time.time() - start_time) < timeout:
        try:
            path = Path(pdf_path)
            
            # Check file exists
            if not path.exists():
                time.sleep(0.1)
                continue
            
            # Check file size > 0
            file_size = path.stat().st_size
            if file_size == 0:
                time.sleep(0.1)
                continue
            
            # Try to read file and verify PDF header
            with open(pdf_path, 'rb') as f:
                header = f.read(5)
                if header == b'%PDF-':
                    logger.info(f"PDF verified ready: {pdf_path} ({file_size} bytes)")
                    return True
                else:
                    # File exists but doesn't have valid PDF header yet
                    time.sleep(0.1)
                    continue
                    
        except (IOError, OSError) as e:
            # File may be locked by another process
            logger.debug(f"PDF not ready, waiting: {e}")
            time.sleep(0.1)
            continue
        except Exception as e:
            logger.warning(f"Unexpected error verifying PDF: {e}")
            return False
    
    logger.warning(f"PDF verification timed out after {timeout}s: {pdf_path}")
    return False


def find_main_tex_file(directory: str) -> Optional[str]:
    """
    Find the main LaTeX file in the given directory.
    
    Strategy (from prototype system):
    1. Check for 00README.json config file
    2. Scan for .tex files containing \\documentclass
    
    Args:
        directory: Path to LaTeX project directory
        
    Returns:
        Path to main .tex file, or None if not found
    """
    dir_path = Path(directory)
    
    # Strategy 1: Check 00README.json config
    readme_path = dir_path / "00README.json"
    if readme_path.exists():
        try:
            with open(readme_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            for source in config.get("sources", []):
                if source.get("usage") == "toplevel":
                    main_file_name = source.get("filename")
                    main_file_path = dir_path / main_file_name
                    if main_file_path.exists():
                        logger.info(f"Found main tex from 00README.json: {main_file_name}")
                        return str(main_file_path)
        except Exception as e:
            logger.warning(f"Failed to parse 00README.json: {e}")
    
    # Strategy 2: Scan for .tex files with \documentclass
    documentclass_pattern = re.compile(r"\\document(class|style)(\[.*?\])?\{.*?\}", re.DOTALL)
    
    tex_files = list(dir_path.glob("*.tex"))
    
    for tex_file in tex_files:
        try:
            with open(tex_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Remove comments before checking
            content = _remove_comments(content)
            
            if documentclass_pattern.search(content):
                logger.info(f"Found main tex by documentclass: {tex_file.name}")
                return str(tex_file)
        except Exception as e:
            logger.warning(f"Failed to read {tex_file}: {e}")
            continue
    
    # Fallback: try common names
    common_names = ["main.tex", "paper.tex", "article.tex"]
    for name in common_names:
        candidate = dir_path / name
        if candidate.exists():
            logger.info(f"Found main tex by common name: {name}")
            return str(candidate)
    
    # Last resort: first .tex file
    if tex_files:
        logger.warning(f"No main tex found, using first file: {tex_files[0].name}")
        return str(tex_files[0])
    
    return None


def _remove_comments(tex: str) -> str:
    """Remove LaTeX comments from content."""
    # Remove \begin{comment}...\end{comment} environments
    tex = re.sub(r'\\begin\s*\{comment\}.*?\\end\s*\{comment\}', '', tex, flags=re.DOTALL)
    
    lines = tex.splitlines()
    cleaned = []
    for line in lines:
        stripped_line = line.lstrip()
        # Skip full-line comments
        if re.match(r'^(?<!\\)%', stripped_line):
            continue
        # Remove inline comments
        line = re.sub(r'(?<!\\)%.*', '', line)
        cleaned.append(line)
    
    return '\n'.join(cleaned)


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
    Compile LaTeX file with latexmk (intelligent build tool)
    
    Uses latexmk for smarter compilation that handles:
    - Multiple compilation passes automatically
    - BibTeX/biber integration
    - Dependency tracking
    
    Args:
        tex_file: Path to .tex file
        output_dir: Output directory
        engine: LaTeX engine ("pdflatex", "xelatex", or "lualatex")
        max_runs: Maximum compilation runs (ignored, latexmk handles this)
    
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
    
    logger.info(f"Compiling {tex_filename} with latexmk ({engine})...")
    
    try:
        # Use latexmk for intelligent compilation
        # -interaction=nonstopmode: continue on errors
        # -outdir: specify output directory
        # -file-line-error: better error messages
        # -synctex=1: for editor integration
        # -f: force mode, continue despite errors
        cmd = [
            "latexmk",
            f"-{engine}",
            "-interaction=nonstopmode",
            f"-outdir={output_dir}",
            "-file-line-error",
            "-synctex=1",
            "-f",  # force mode
            tex_filename
        ]
        
        # Run compilation with binary mode to avoid encoding issues on Windows
        result = subprocess.run(
            cmd,
            cwd=str(tex_path.parent),
            capture_output=True,
            text=False,  # Binary mode to avoid Windows gbk encoding issues
            timeout=600  # 10 minute timeout for latexmk
        )
        
        last_exit_code = result.returncode
        
        logger.info(f"latexmk ({engine}) completed with exit code {result.returncode}")
        
    except subprocess.TimeoutExpired:
        logger.error(f"latexmk ({engine}) compilation timed out")
        return CompilationResult(success=False, exit_code=-2)
    except FileNotFoundError:
        logger.warning("latexmk not found, falling back to direct compiler call")
        return _compile_latex_direct(tex_file, output_dir, engine, max_runs)
    except Exception as e:
        logger.error(f"latexmk ({engine}) compilation failed: {e}")
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
        f"latexmk ({engine}) result: "
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


def _compile_latex_direct(
    tex_file: str,
    output_dir: str,
    engine: str = "pdflatex",
    max_runs: int = 2
) -> CompilationResult:
    """
    Fallback: Compile LaTeX file directly with pdflatex/xelatex
    Used when latexmk is not available.
    """
    tex_path = Path(tex_file)
    tex_filename = tex_path.name
    tex_basename = tex_path.stem
    out_path = Path(output_dir)
    
    logger.info(f"Compiling {tex_filename} directly with {engine}...")
    
    last_exit_code = 0
    for run in range(max_runs):
        try:
            from backend.app.core.config import settings
            
            if settings.latex_bin_dir and os.path.exists(settings.latex_bin_dir):
                engine_path = os.path.join(settings.latex_bin_dir, f"{engine}.exe")
                if not os.path.exists(engine_path):
                    logger.error(f"Compiler not found: {engine_path}")
                    return CompilationResult(success=False, exit_code=-3)
            else:
                engine_path = engine
            
            cmd = [
                engine_path,
                "-interaction=nonstopmode",
                "-output-directory", str(output_dir),
                tex_filename
            ]
            
            result = subprocess.run(
                cmd,
                cwd=str(tex_path.parent),
                capture_output=True,
                text=False,  # Binary mode to avoid encoding issues
                timeout=300
            )
            
            last_exit_code = result.returncode
            logger.info(f"{engine} run {run + 1}/{max_runs} completed with exit code {result.returncode}")
            
        except subprocess.TimeoutExpired:
            logger.error(f"{engine} compilation timed out")
            return CompilationResult(success=False, exit_code=-2)
        except Exception as e:
            logger.error(f"{engine} compilation failed: {e}")
            return CompilationResult(success=False, exit_code=-3)
    
    pdf_path = out_path / f"{tex_basename}.pdf"
    log_path = out_path / f"{tex_basename}.log"
    pdf_exists = pdf_path.exists()
    
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


def compile_with_intelligent_fallback(
    tex_file: str, 
    output_dir: str,
    preferred_order: Optional[List[str]] = None
) -> Dict:
    """
    Intelligent LaTeX compilation with three-engine fallback strategy
    
    Strategy:
    1. Detect document language if no preferred_order is specified
    2. For CJK documents: XeLaTeX → LuaLaTeX → PDFLaTeX
    3. For Latin documents: PDFLaTeX → XeLaTeX → LuaLaTeX
    4. Try each engine in order
    5. If perfect compilation (zero errors), return immediately
    6. Otherwise, collect all results and select the best PDF
    7. If all engines fail to produce PDF, return failure with source files
    
    Args:
        tex_file: Path to .tex file
        output_dir: Output directory
        preferred_order: Optional list of engines to try in order
                        e.g., ["xelatex", "lualatex", "pdflatex"]
                        If not provided, auto-detect based on document language
    
    Returns:
        Dictionary with:
        - pdf_path: Path to best PDF (None if all failed)
        - status: "completed" | "completed_with_warnings" | "failed_compilation"
        - engine: Engine that produced the PDF
        - error_count: Number of errors in selected PDF
        - warnings: Warning message if errors present
        - errors: Combined error details if compilation failed
    """
    logger.info(f"Starting intelligent three-engine compilation for {tex_file}")
    
    # Determine engine order
    if preferred_order is not None:
        engines = preferred_order
        logger.info(f"Using custom engine order: {engines}")
    else:
        # Auto-detect language
        language = detect_document_language(tex_file)
        if language == "cjk":
            engines = ["xelatex", "lualatex", "pdflatex"]
            logger.info(f"Detected CJK document, using engine order: {engines}")
        else:
            engines = ["pdflatex", "xelatex", "lualatex"]
            logger.info(f"Detected Latin document, using engine order: {engines}")
    
    # Collect results from all engines
    results: Dict[str, CompilationResult] = {}
    
    for engine in engines:
        logger.info(f"⚡ Attempting compilation with {engine}...")
        result = compile_latex(tex_file, output_dir, engine=engine)
        results[engine] = result
        
        # Perfect compilation - return immediately
        if result.success and result.error_count == 0:
            logger.info(f"✅ {engine} produced perfect compilation (zero errors)")
            return {
                "pdf_path": result.pdf_path,
                "status": "completed",
                "engine": engine,
                "error_count": 0,
                "warnings": None,
                "errors": None
            }
    
    # No perfect compilation - select best result
    # Find all engines that produced PDFs
    engines_with_pdf = [
        (engine, result) 
        for engine, result in results.items() 
        if result.pdf_path is not None
    ]
    
    if engines_with_pdf:
        # Sort by error count (ascending)
        engines_with_pdf.sort(key=lambda x: x[1].error_count)
        best_engine, best_result = engines_with_pdf[0]
        
        # Build comparison string
        comparison = ", ".join(
            f"{engine}: {result.error_count}" 
            for engine, result in results.items()
        )
        
        logger.warning(
            f"⚠️ Selected {best_engine} PDF with {best_result.error_count} errors "
            f"({comparison})"
        )
        
        return {
            "pdf_path": best_result.pdf_path,
            "status": "completed_with_warnings",
            "engine": best_engine,
            "error_count": best_result.error_count,
            "warnings": f"Compilation completed with {best_result.error_count} errors using {best_engine}.",
            "errors": None
        }
    
    # All engines failed to produce PDF
    logger.error(f"❌ All engines failed to produce PDF: {engines}")
    
    # Combine error messages
    combined_errors = "Compilation failed with all engines:\n\n"
    for engine, result in results.items():
        combined_errors += f"{engine} ({result.error_count} errors):\n"
        combined_errors += "\n".join(result.errors[:10]) + "\n\n"
    
    total_errors = sum(result.error_count for result in results.values())
    
    return {
        "pdf_path": None,
        "status": "failed_compilation",
        "engine": None,
        "error_count": total_errors,
        "warnings": None,
        "errors": combined_errors
    }


def compile_with_fallback(tex_file: str, output_dir: str) -> Dict:
    """
    Intelligent LaTeX compilation with fallback strategy (backward compatible)
    
    This function is kept for backward compatibility.
    It now delegates to compile_with_intelligent_fallback.
    
    Strategy:
    1. Auto-detect document language
    2. For CJK: XeLaTeX → LuaLaTeX → PDFLaTeX
    3. For Latin: PDFLaTeX → XeLaTeX → LuaLaTeX
    4. Try each engine, return best result
    
    Args:
        tex_file: Path to .tex file
        output_dir: Output directory
    
    Returns:
        Dictionary with pdf_path, status, engine, error_count, warnings, errors
    """
    return compile_with_intelligent_fallback(tex_file, output_dir)


# Keep the old compile_with_fallback_legacy for reference (can be removed later)
def _compile_with_fallback_legacy(tex_file: str, output_dir: str) -> Dict:
    """
    Legacy two-engine fallback strategy (pdflatex then xelatex)
    
    Kept for reference. Use compile_with_intelligent_fallback instead.
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
        # Use intelligent main tex file detection
        main_tex = find_main_tex_file(self.output_latex_dir)
        
        if not main_tex:
            logger.error(f"No main .tex file found in {self.output_latex_dir}")
            return None
        
        logger.info(f"Compiling {Path(main_tex).name}...")
        
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

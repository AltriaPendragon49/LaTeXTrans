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
import asyncio
import logging
import json
import shutil
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, List, Protocol, Callable
import platform
import signal
from .sanitizer import try_sanitize_images_in_errors, apply_precompile_sanitization

logger = logging.getLogger(__name__)

LATEX_RUNTIME_MODE_ENV = "LATEX_RUNTIME_MODE"
LATEX_RUNTIME_MODE_HOST = "host"
LATEX_RUNTIME_MODE_DOCKER = "docker"
LATEX_DOCKER_IMAGE_ENV = "LATEX_DOCKER_IMAGE"
LATEX_DOCKER_IMAGE_DEFAULT = "latextrans-runtime:texlive2025"


class LatexExecutor(Protocol):
    """Build final subprocess argv from an already constructed LaTeX command."""

    def prepare_command(self, cmd: List[str], cwd: Path) -> List[str]:
        ...


class HostLatexExecutor:
    """Preserve existing behavior by running commands directly on host."""

    def prepare_command(self, cmd: List[str], cwd: Path) -> List[str]:
        return cmd


class DockerLatexExecutor:
    """Wrap LaTeX commands with docker run while preserving command arguments."""

    def __init__(self, image: str):
        self.image = image or LATEX_DOCKER_IMAGE_DEFAULT

    def prepare_command(self, cmd: List[str], cwd: Path) -> List[str]:
        cwd_path = cwd.resolve()
        rewritten_cmd, extra_mounts = self._rewrite_command_paths(cmd, cwd_path)
        docker_cmd = [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{cwd_path}:/work",
            "-w",
            "/work",
        ]
        for host_path, container_path in extra_mounts:
            docker_cmd.extend(["-v", f"{host_path}:{container_path}"])

        docker_cmd.append(self.image)
        docker_cmd.extend(rewritten_cmd)
        return docker_cmd

    def _rewrite_command_paths(self, cmd: List[str], cwd: Path) -> Tuple[List[str], List[Tuple[Path, str]]]:
        rewritten = list(cmd)
        mounts: List[Tuple[Path, str]] = []

        if rewritten:
            executable = rewritten[0]
            if executable.lower().endswith(".exe"):
                rewritten[0] = Path(executable).stem
            elif os.path.sep in executable or "/" in executable or "\\" in executable:
                rewritten[0] = Path(executable).name

        for i, arg in enumerate(rewritten):
            if arg.startswith("-outdir="):
                host_outdir = Path(arg.split("=", 1)[1]).resolve()
                container_outdir = self._map_host_path(host_outdir, cwd, mounts, "/latex-out")
                rewritten[i] = f"-outdir={container_outdir}"
                continue

            if arg == "-output-directory" and i + 1 < len(rewritten):
                host_outdir = Path(rewritten[i + 1]).resolve()
                container_outdir = self._map_host_path(host_outdir, cwd, mounts, "/latex-out")
                rewritten[i + 1] = container_outdir

        return rewritten, mounts

    @staticmethod
    def _map_host_path(host_path: Path, cwd: Path, mounts: List[Tuple[Path, str]], default_container_path: str) -> str:
        try:
            relative = host_path.relative_to(cwd)
            relative_posix = relative.as_posix()
            return "/work" if relative_posix == "." else f"/work/{relative_posix}"
        except ValueError:
            if not any(existing_host == host_path for existing_host, _ in mounts):
                mounts.append((host_path, default_container_path))
            return default_container_path


def _get_latex_executor() -> LatexExecutor:
    runtime_mode = os.getenv(LATEX_RUNTIME_MODE_ENV, LATEX_RUNTIME_MODE_DOCKER).strip().lower()
    if runtime_mode == LATEX_RUNTIME_MODE_HOST:
        return HostLatexExecutor()
    if runtime_mode == LATEX_RUNTIME_MODE_DOCKER:
        if _is_running_in_container():
            logger.warning(
                "Detected container runtime; forcing HostLatexExecutor to avoid nested docker run."
            )
            return HostLatexExecutor()
        if not _is_docker_available():
            logger.warning(
                "Docker runtime mode requested but docker is unavailable; forcing HostLatexExecutor."
            )
            return HostLatexExecutor()
        image = os.getenv(LATEX_DOCKER_IMAGE_ENV, LATEX_DOCKER_IMAGE_DEFAULT).strip()
        return DockerLatexExecutor(image=image or LATEX_DOCKER_IMAGE_DEFAULT)
    logger.warning(
        "Unknown %s=%r, fallback to HostLatexExecutor",
        LATEX_RUNTIME_MODE_ENV,
        runtime_mode,
    )
    return HostLatexExecutor()


def _is_running_in_container() -> bool:
    if Path("/.dockerenv").exists():
        return True

    cgroup_path = Path("/proc/1/cgroup")
    if cgroup_path.exists():
        try:
            content = cgroup_path.read_text(encoding="utf-8", errors="ignore").lower()
            markers = ("docker", "containerd", "kubepods", "podman")
            return any(marker in content for marker in markers)
        except OSError:
            return False
    return False


def _is_docker_available() -> bool:
    docker_path = shutil.which("docker")
    if not docker_path:
        return False
    try:
        probe = subprocess.run(
            [docker_path, "version", "--format", "{{.Server.Version}}"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        return probe.returncode == 0
    except Exception:
        return False


def _kill_process_tree(pid: int) -> None:
    """
    Kill a process and all its children (entire process tree).
    
    On Windows, subprocess timeout only kills the parent process,
    leaving child processes (e.g. xelatex spawned by latexmk) as orphans.
    This function uses 'taskkill /T /F' on Windows to kill the entire tree.
    On Unix, it sends SIGTERM to the process group.
    """
    try:
        if platform.system() == "Windows":
            # /T = kill child processes, /F = force, /PID = process id
            subprocess.run(
                ["taskkill", "/T", "/F", "/PID", str(pid)],
                capture_output=True,
                timeout=10
            )
        else:
            os.killpg(os.getpgid(pid), signal.SIGTERM)
    except Exception as e:
        logger.warning(f"Failed to kill process tree for PID {pid}: {e}")
        # Fallback: try to kill just the process
        try:
            os.kill(pid, signal.SIGTERM)
        except Exception:
            pass


async def _spawn_latex_process_async(final_cmd: List[str], cwd: Path) -> asyncio.subprocess.Process:
    """
    Spawn LaTeX subprocess in its own process group/session for robust cancellation.
    """
    kwargs: Dict[str, Any] = {
        "cwd": str(cwd),
        "stdout": asyncio.subprocess.PIPE,
        "stderr": asyncio.subprocess.PIPE,
    }
    if platform.system() == "Windows":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        kwargs["start_new_session"] = True
    return await asyncio.create_subprocess_exec(*final_cmd, **kwargs)


async def _terminate_process_tree_and_wait(proc: asyncio.subprocess.Process) -> None:
    """
    Kill full process tree then wait for process object to complete.
    """
    if proc is None or proc.pid is None:
        return
    await asyncio.to_thread(_kill_process_tree, int(proc.pid))
    try:
        await asyncio.wait_for(proc.wait(), timeout=10)
    except Exception:
        pass

# CJK character detection threshold
CJK_THRESHOLD = 100

# CJK quality-gate threshold:
# if "Missing character: There is no ..." appears at or above this count,
# we treat the engine output as quality-degraded for CJK selection.
CJK_MISSING_CHAR_SEVERE_THRESHOLD = 50

# Maximum content to read for language detection (100KB)
MAX_DETECTION_CONTENT = 100 * 1024

# Maximum number of image-sanitizer rounds before giving up.
# Each round repairs only *newly discovered* corrupted PDFs, so the loop is
# monotonically convergent.  This constant is a hard safety cap.
MAX_SANITIZE_ROUNDS = 20

_CJK_TARGET_LANGS = {"zh", "ch", "ja", "ko"}
_CYRILLIC_TARGET_LANGS = {"ru", "uk", "bg", "sr", "mk", "be"}


def _normalize_language_code(language_code: Optional[str]) -> str:
    if not language_code:
        return ""
    code = str(language_code).strip().lower().replace("_", "-")
    if "-" in code:
        return code.split("-", 1)[0]
    return code


def map_target_language_to_family(target_language: Optional[str]) -> Optional[str]:
    """
    Map target language code to compiler language family.

    Returns:
        "cjk", "cyrillic", "latin", or None (when not provided).
    """
    normalized = _normalize_language_code(target_language)
    if not normalized:
        return None
    if normalized in _CJK_TARGET_LANGS:
        return "cjk"
    if normalized in _CYRILLIC_TARGET_LANGS:
        return "cyrillic"
    return "latin"


_INPUT_INCLUDE_RE = re.compile(r'\\(?:input|include)\{([^}]+)\}')


def _resolve_include_tex_path(base_dir: Path, include_name: str) -> Optional[Path]:
    """Resolve a LaTeX \\input/\\include target to an existing .tex path."""
    if not include_name:
        return None
    raw = include_name.strip()
    if not raw:
        return None

    candidate = (base_dir / raw).resolve()
    if candidate.exists() and candidate.is_file():
        return candidate

    if not candidate.suffix:
        with_tex = candidate.with_suffix(".tex")
        if with_tex.exists() and with_tex.is_file():
            return with_tex

    return None


def collect_detection_content(tex_file: str, max_chars: int = MAX_DETECTION_CONTENT) -> str:
    """
    Read main tex + recursively included tex files for language detection.

    The traversal is bounded by `max_chars` and skips repeated files.
    """
    visited: set[str] = set()

    def _collect(path: Path, budget: int) -> str:
        if budget <= 0:
            return ""
        key = str(path.resolve())
        if key in visited:
            return ""
        visited.add(key)
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return ""

        chunks: List[str] = []
        local = content[:budget]
        chunks.append(local)
        consumed = len(local)
        remaining = budget - consumed
        if remaining <= 0:
            return "".join(chunks)

        sanitized = _remove_comments(local)
        for m in _INPUT_INCLUDE_RE.finditer(sanitized):
            if remaining <= 0:
                break
            include_path = _resolve_include_tex_path(path.parent, m.group(1))
            if not include_path:
                continue
            child = _collect(include_path, remaining)
            if not child:
                continue
            chunks.append("\n")
            chunks.append(child)
            consumed += 1 + len(child)
            remaining = budget - consumed

        return "".join(chunks)

    return _collect(Path(tex_file).resolve(), max_chars)


def detect_document_language_from_content(content: str) -> str:
    """
    Detect document language from text content.
    
    Checks for CJK (Chinese, Japanese, Korean) and Cyrillic characters.
    
    Args:
        content: Text content to analyze
        
    Returns:
        "cjk" if CJK characters exceed threshold,
        "cyrillic" if Cyrillic characters exceed threshold,
        otherwise "latin"
    """
    import re
    
    # CJK character ranges:
    # - Chinese: \u4e00-\u9fff (CJK Unified Ideographs)
    # - Japanese Hiragana: \u3040-\u309f
    # - Japanese Katakana: \u30a0-\u30ff  
    # - Korean Hangul: \uac00-\ud7af
    cjk_pattern = re.compile(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]')
    
    # Cyrillic character ranges:
    # - Basic Cyrillic: \u0400-\u04ff (Russian, Ukrainian, Bulgarian, Serbian, etc.)
    cyrillic_pattern = re.compile(r'[\u0400-\u04ff]')
    
    cjk_count = len(cjk_pattern.findall(content))
    cyrillic_count = len(cyrillic_pattern.findall(content))
    
    if cjk_count > CJK_THRESHOLD:
        return "cjk"
    if cyrillic_count > 50:  # Lower threshold: even sparse Cyrillic needs XeLaTeX
        return "cyrillic"
    return "latin"


def detect_document_language(tex_file: str, include_inputs: bool = False) -> str:
    """
    Detect the primary language type of a LaTeX document.
    
    Strategy:
    1. Read the .tex file content (up to 100KB)
    2. Count CJK characters (Chinese, Japanese, Korean)
    3. Count Cyrillic characters (Russian, Ukrainian, Bulgarian, etc.)
    4. Classify as "cjk", "cyrillic", or "latin"
    
    Args:
        tex_file: Path to .tex file
        
    Returns:
        "cjk", "cyrillic", or "latin"
    """
    try:
        if include_inputs:
            content = collect_detection_content(tex_file, MAX_DETECTION_CONTENT)
        else:
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
    
    Strategy (enhanced with subdirectory support):
    1. Check for 00README.json config file (in top-level and subdirs)
    2. Scan for .tex files containing \\documentclass
    3. If no .tex in top-level, search subdirectories (for ZIP extraction case)
    
    Args:
        directory: Path to LaTeX project directory
        
    Returns:
        Path to main .tex file, or None if not found
    """
    dir_path = Path(directory)
    
    # Helper function to find main tex in a specific directory
    def _find_in_dir(search_dir: Path) -> Optional[str]:
        """Search for main tex file in a single directory."""
        # Strategy 1: Check 00README.json config
        readme_path = search_dir / "00README.json"
        if readme_path.exists():
            try:
                with open(readme_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                for source in config.get("sources", []):
                    if source.get("usage") == "toplevel":
                        main_file_name = source.get("filename")
                        main_file_path = search_dir / main_file_name
                        if main_file_path.exists():
                            logger.info(f"Found main tex from 00README.json: {main_file_name}")
                            return str(main_file_path)
            except Exception as e:
                logger.warning(f"Failed to parse 00README.json: {e}")
        
        # Strategy 2: Scan for .tex files with \documentclass
        documentclass_pattern = re.compile(r"\\document(class|style)(\[.*?\])?\{.*?\}", re.DOTALL)
        
        tex_files = list(search_dir.glob("*.tex"))
        
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
            candidate = search_dir / name
            if candidate.exists():
                logger.info(f"Found main tex by common name: {name}")
                return str(candidate)
        
        # Last resort: first .tex file
        if tex_files:
            logger.warning(f"No main tex found, using first file: {tex_files[0].name}")
            return str(tex_files[0])
        
        return None
    
    # First, try to find in the top-level directory
    result = _find_in_dir(dir_path)
    if result:
        return result
    
    # If not found in top-level, check subdirectories
    # This handles ZIP extraction case: task_id/project_name/main.tex
    logger.info(f"No tex files in top-level, searching subdirectories of {dir_path}")
    
    # Get all immediate subdirectories (excluding hidden dirs and common non-project dirs)
    subdirs = [
        d for d in dir_path.iterdir() 
        if d.is_dir() and not d.name.startswith('.') and d.name not in ('__pycache__', '.git')
    ]
    
    # Sort by name to be deterministic
    subdirs.sort(key=lambda x: x.name)
    
    for subdir in subdirs:
        result = _find_in_dir(subdir)
        if result:
            logger.info(f"Found main tex in subdirectory: {subdir.name}")
            return result
    
    # Last resort: recursive search for any .tex file with documentclass
    logger.warning(f"Searching recursively for any .tex file with documentclass in {dir_path}")
    documentclass_pattern = re.compile(r"\\document(class|style)(\[.*?\])?\{.*?\}", re.DOTALL)
    
    for tex_file in dir_path.rglob("*.tex"):
        try:
            with open(tex_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            content = _remove_comments(content)
            if documentclass_pattern.search(content):
                logger.info(f"Found main tex via recursive search: {tex_file}")
                return str(tex_file)
        except Exception as e:
            continue
    
    logger.error(f"No main tex file found in {dir_path} or any subdirectories")
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
        exit_code: int = 0,
        quality_issue_count: int = 0,
        quality_issues: Optional[List[str]] = None,
        quality_issue_severe: bool = False,
    ):
        self.success = success
        self.pdf_path = pdf_path
        self.log_path = log_path
        self.error_count = error_count
        self.errors = errors or []
        self.exit_code = exit_code
        self.quality_issue_count = quality_issue_count
        self.quality_issues = quality_issues or []
        self.quality_issue_severe = quality_issue_severe


def _remove_stale_expected_pdf(pdf_path: Path) -> None:
    """
    Remove stale expected output PDF before an engine run.

    Some source bundles include a prebuilt PDF with the same basename as the
    main TeX file (for example `main.pdf`). If compilation fails and that stale
    file remains, it can be misclassified as newly compiled output.
    """
    if not pdf_path.exists():
        return
    try:
        pdf_path.unlink()
        logger.info(f"Removed stale PDF before compilation: {pdf_path}")
    except Exception as exc:
        logger.warning(f"Failed to remove stale PDF {pdf_path}: {exc}")


def parse_log_errors(log_path: str) -> Tuple[int, List[str]]:
    """
    Parse LaTeX .log file and count errors
    
    Supports both classic LaTeX log style ("! LaTeX Error ...") and
    file-line-error style ("file.tex:123: LaTeX Error ...").
    
    Args:
        log_path: Path to .log file
    
    Returns:
        Tuple of (error_count, error_lines)
    """
    if not os.path.exists(log_path):
        return 0, []
    
    error_patterns = [
        # Classic TeX/LaTeX error format
        r"^! LaTeX Error",
        r"^! Package .* Error",
        r"^! Undefined control sequence",
        r"^! Missing",
        r"^! File ended while scanning use of .+",
        r"^! Emergency stop",
        r"^! .*Error",
        r"^Runaway argument\?$",
        r"^\*\*\* \(job aborted, no legal \\end found\)",
        # -file-line-error format (latexmk default in this project)
        # Note: LuaLaTeX sometimes starts these lines with an opening '(',
        # so we allow an optional leading '(' via the \(? prefix.
        r"^\(?\s*.+:\d+:\s+LaTeX Error:",
        r"^\(?\s*.+:\d+:\s+Package .* Error:",
        r"^\(?\s*.+:\d+:\s+Undefined control sequence\.?$",
        r"^\(?\s*.+:\d+:\s+Missing .+ inserted\.?$",
        r"^\(?\s*.+:\d+:\s+File ended while scanning use of .+",
        r"^\(?\s*.+:\d+:\s+Extra .+$",
        r"^\(?\s*>?.+:\d+:\s*(?:fatal\s+)?error:",
        # Fatal fallback signatures
        r"^.+Fatal error occurred, no output PDF file produced!?$",
        r"^Emergency stop\.$",
        # Specific triggers (image-related, may span continuation lines)
        r"reading image failed",
        r"pdf inclusion",
    ]
    compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in error_patterns]
    # Patterns that indicate this line is a continuation (image errors often wrap)
    _IMAGE_ERROR_KEYWORDS = ("reading image failed", "pdf inclusion")
    root_cause_hint_patterns = [
        re.compile(r"^Runaway argument\?$"),
        re.compile(r"^! File ended while scanning use of .+"),
        re.compile(r"^.+:\d+:\s+File ended while scanning use of .+"),
        re.compile(r"^\*\*\* \(job aborted, no legal \\end found\)"),
    ]
    
    errors = []
    
    try:
        prev_nonempty = ""
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            all_lines = [l.rstrip('\n\r') for l in f]
        
        i = 0
        while i < len(all_lines):
            line = all_lines[i].strip()
            i += 1
            if not line:
                continue

            if any(pattern.search(line) for pattern in compiled_patterns):
                # Join continuation lines — LaTeX logs wrap at ~79 chars.
                # For image-related errors, keep merging forward until the
                # full keyword appears or we hit a blank line / new error.
                merged = line
                look_ahead_limit = 4  # safety cap: never merge more than 4 lines
                merges = 0
                while i < len(all_lines) and merges < look_ahead_limit:
                    next_line = all_lines[i].strip()
                    if not next_line:
                        break  # blank line terminates continuation
                    if any(pattern.search(next_line) for pattern in compiled_patterns):
                        # Only skip the merge if the next line is a *new* error,
                        # not the continuation of the current image error.
                        if any(kw in merged.lower() for kw in _IMAGE_ERROR_KEYWORDS):
                            break  # image error already complete
                        if not any(kw in (merged + next_line).lower() for kw in _IMAGE_ERROR_KEYWORDS):
                            break  # unrelated new error
                    merged = merged + next_line
                    i += 1
                    merges += 1
                    # Stop early if the image-error keyword is now complete
                    if any(kw in merged.lower() for kw in _IMAGE_ERROR_KEYWORDS):
                        break
                line = merged

                if "Emergency stop" in line and prev_nonempty:
                    if any(pattern.search(prev_nonempty) for pattern in root_cause_hint_patterns):
                        if not errors or errors[-1] != prev_nonempty:
                            errors.append(prev_nonempty)
                # Avoid noisy duplicate lines in summaries.
                if not errors or errors[-1] != line:
                    errors.append(line)
            prev_nonempty = line
    except Exception as e:
        logger.warning(f"Failed to parse log file {log_path}: {e}")
        return 0, []
    
    return len(errors), errors


def parse_log_quality_issues(
    log_path: str,
    enable_quality_gate: bool = False,
    severe_threshold: int = CJK_MISSING_CHAR_SEVERE_THRESHOLD,
    max_samples: int = 10,
) -> Tuple[int, List[str], bool]:
    """
    Parse LaTeX .log for display-quality issues that do not surface as hard errors.

    Today we specifically track missing glyph diagnostics:
      "Missing character: There is no ... in font ..."

    Args:
        log_path: Path to .log file
        enable_quality_gate: If False, parsing is bypassed (returns zeros)
        severe_threshold: Count threshold considered severe
        max_samples: Max sample lines to retain for diagnostics

    Returns:
        Tuple of (issue_count, sample_lines, is_severe)
    """
    if not enable_quality_gate:
        return 0, [], False
    if not os.path.exists(log_path):
        return 0, [], False

    issue_count = 0
    samples: List[str] = []
    marker = "Missing character: There is no"

    try:
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line:
                    continue
                if marker in line:
                    issue_count += 1
                    if len(samples) < max_samples:
                        samples.append(line)
    except Exception as e:
        logger.warning(f"Failed to parse quality issues from log {log_path}: {e}")
        return 0, [], False

    return issue_count, samples, issue_count >= severe_threshold


def _extract_content_between_braces(text: str, start_index: int) -> str:
    """Extracts content inside { } taking into account nested braces."""
    brace_count = 0
    in_braces = False
    content = []
    for i in range(start_index, len(text)):
        char = text[i]
        if char == '{':
            if in_braces: content.append(char)
            brace_count += 1
            in_braces = True
        elif char == '}':
            brace_count -= 1
            if brace_count == 0 and in_braces: return "".join(content)
            if in_braces: content.append(char)
        elif in_braces:
            content.append(char)
    return "".join(content)

def _fallback_biblatex_to_thebibliography(tex_dir: str, output_dir: str) -> None:
    """
    Fallback for biblatex projects without .bib files (like many arXiv submissions).
    Modern biblatex cannot parse older format .bbl files, causing raw data spill.
    This parses the old .bbl manually and replaces \printbibliography
    with a raw thebibliography environment, removing the biblatex dependency entirely.
    """
    bbl_path = None
    for search_dir in [output_dir, tex_dir]:
        for bbl in Path(search_dir).rglob("*.bbl"):
            try:
                content = bbl.read_text(encoding='utf-8', errors='replace')
                if 'biblatex bbl format version' in content:
                    bbl_path = bbl
                    break
            except Exception:
                pass
        if bbl_path: break
        
    if not bbl_path:
        return
        
    bbl_content = bbl_path.read_text(encoding='utf-8', errors='replace')
    entries = []
    parts = bbl_content.split(r'\entry{')
    for part in parts[1:]:
        if r'\endentry' not in part: continue
        entry_text = part.split(r'\endentry')[0]
        
        id_end = entry_text.find('}')
        if id_end == -1: continue
        entry_id = entry_text[:id_end]
        
        title = ""
        title_idx = entry_text.find(r'\field{title}{')
        if title_idx != -1:
            title = _extract_content_between_braces(entry_text, title_idx + 13)
            title = re.sub(r'\s+', ' ', title).strip()
            
        year = ""
        year_idx = entry_text.find(r'\field{year}{')
        if year_idx != -1:
            year = _extract_content_between_braces(entry_text, year_idx + 12)
            
        authors = []
        author_block_idx = entry_text.find(r'\name{author}')
        if author_block_idx != -1:
            end_author_idx = entry_text.find(r'\name{', author_block_idx + 1)
            if end_author_idx == -1: end_author_idx = entry_text.find(r'\list{')
            if end_author_idx == -1: end_author_idx = len(entry_text)
            author_text = entry_text[author_block_idx:end_author_idx]
            
            hash_blocks = author_text.split('{{hash=')
            for hb in hash_blocks[1:]:
                # Extract family
                fam_idx = hb.find('family={')
                fam_str = ""
                if fam_idx != -1:
                    fam_str = _extract_content_between_braces(hb, fam_idx + 7)
                    
                # Extract given
                giv_idx = hb.find('given={')
                giv_str = ""
                if giv_idx != -1:
                    giv_str = _extract_content_between_braces(hb, giv_idx + 6)
                
                author_str = ""
                if giv_str:
                    g = re.sub(r'\\bibnamedelima\s*', ' ', giv_str)
                    g = re.sub(r'\\[a-zA-Z]+', '', g) 
                    author_str += g.strip() + " "
                if fam_str:
                    f = re.sub(r'\\bibnamedelima\s*', ' ', fam_str)
                    f = re.sub(r'\\[a-zA-Z]+', '', f)
                    author_str += f.strip()
                if author_str: authors.append(author_str.strip())
        
        author_final = " and ".join(authors) if authors else "Unknown Author"
        if not title: title = "Unknown Title"
        entries.append({'id': entry_id, 'author': author_final, 'title': title, 'year': year})

    if not entries: return
    
    out = ["\\begin{thebibliography}{99}"]
    for e in entries:
        item = f"\\bibitem{{{e['id']}}} {e['author']}. \\textit{{{e['title']}}}."
        if e['year']: item += f" {e['year']}."
        out.append(item)
    out.append("\\end{thebibliography}")
    bibliography_str = '\n'.join(out)
    
    # Now patch the .tex files
    patched = False
    for search_dir in [output_dir, tex_dir]:
        for tex_path in Path(search_dir).rglob("*.tex"):
            try:
                tex_content = tex_path.read_text(encoding='utf-8', errors='replace')
                orig_content = tex_content
                
                # Disable biblatex import 
                if 'biblatex' in tex_content:
                    tex_content = re.sub(r'\\usepackage\[[^\]]*\]\{biblatex\}', r'% \\usepackage{biblatex}', tex_content)
                    tex_content = re.sub(r'\\usepackage\{biblatex\}', r'% \\usepackage{biblatex}', tex_content)
                    tex_content = re.sub(r'\\addbibresource\{[^}]+\}', r'% \\addbibresource', tex_content)
                    tex_content = re.sub(r'\\makeatletter\\def\\blx@bblversion\{[^}]+\}\\makeatother', '', tex_content)
                    
                    # Replace \printbibliography (with or without options)
                    if bibliography_str:
                        # Ensure special regex chars in bibliography_str act as raw replacement string
                        replacement = bibliography_str.replace('\\', '\\\\')
                        tex_content = re.sub(r'\\printbibliography\[[^\]]*\]', replacement, tex_content)
                        tex_content = re.sub(r'\\printbibliography', replacement, tex_content)
                
                # Double-check: some documents might just use \makeatletter... hack left over
                if 'blx@bblversion' in tex_content:
                    tex_content = re.sub(r'\\makeatletter\\def\\blx@bblversion\{[^}]+\}\\makeatother', '', tex_content)

                if tex_content != orig_content:
                    tex_path.write_text(tex_content, encoding='utf-8')
                    logger.info(f"Replaced biblatex with {len(entries)}-entry thebibliography fallback in {tex_path}")
                    patched = True
            except Exception as e:
                logger.warning(f"Failed to patch tex file {tex_path}: {e}")
                
    if patched:
        logger.info(f"Successfully applied biblatex fallback using raw {bbl_path.name}")


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
    tex_path = Path(tex_file).resolve()
    out_path = Path(output_dir).resolve()

    if not tex_path.exists():
        logger.error(f"TeX file not found: {tex_file}")
        return CompilationResult(success=False, exit_code=-1)

    tex_filename = tex_path.name
    tex_basename = tex_path.stem
    
    # Prepare output directory
    out_path.mkdir(parents=True, exist_ok=True)
    pdf_path = out_path / f"{tex_basename}.pdf"
    log_path = out_path / f"{tex_basename}.log"
    _remove_stale_expected_pdf(pdf_path)
    
    logger.info(f"Compiling {tex_filename} with latexmk ({engine})...")
    
    try:
        # Use latexmk for intelligent compilation
        # -interaction=nonstopmode: don't stop for missing files etc.
        # NOTE: -halt-on-error intentionally OMITTED. LaTeX's nonstopmode error recovery
        # allows many documents with minor errors (e.g. math formatting, missing glyphs)
        # to still produce a readable PDF. Halting on first error drastically reduces
        # the PDF yield for real-world arXiv papers.
        # -outdir: specify output directory
        # -file-line-error: better error messages
        # -synctex=1: for editor integration
        
        # Detect if project has real .bib files (excluding auto-generated *-blx.bib by biblatex)
        # ArXiv submissions often include pre-built .bbl without .bib files.
        # Forcing -bibtex in that case causes bibtex to fail and overwrite the .bbl with an empty one.
        tex_dir = tex_path.parent
        has_real_bib = any(
            not bib.name.endswith("-blx.bib")
            for bib in Path(tex_dir).rglob("*.bib")
        )
        bibtex_flag = "-bibtex" if has_real_bib else "-bibtex-"
        logger.info(f"Bibliography detection: {'found' if has_real_bib else 'no'} .bib files -> using {bibtex_flag}")

        # When no .bib files exist, we must use a fallback to standard thebibliography
        # because modern biblatex v3.3+ cannot parse older biblatex v3.2 .bbl format 
        # (causes undefined control sequences or text garbling).
        if not has_real_bib:
            _fallback_biblatex_to_thebibliography(str(tex_dir), str(out_path))
        
        
        cmd = [
            "latexmk",
            f"-{engine}",
            "-interaction=nonstopmode",
            f"-outdir={out_path}",
            "-file-line-error",
            "-synctex=1",
            bibtex_flag,  # conditionally run bibtex (skip if no .bib to preserve existing .bbl)
            tex_filename
        ]
        executor = _get_latex_executor()
        final_cmd = executor.prepare_command(cmd, tex_dir)
        
        # Use Popen instead of subprocess.run to properly kill the entire process tree
        # on timeout. On Windows, subprocess.run timeout only kills the parent (latexmk),
        # leaving child processes (xelatex/lualatex) as orphans that hang forever.
        import time
        compilation_timeout = 300  # 5 minutes per engine attempt
        
        proc = subprocess.Popen(
            final_cmd,
            cwd=str(tex_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        
        try:
            stdout, stderr = proc.communicate(timeout=compilation_timeout)
            last_exit_code = proc.returncode
            logger.info(f"latexmk ({engine}) completed with exit code {proc.returncode}")
        except subprocess.TimeoutExpired:
            logger.error(f"latexmk ({engine}) compilation timed out after {compilation_timeout}s, killing process tree (PID {proc.pid})...")
            _kill_process_tree(proc.pid)
            proc.wait(timeout=10)  # Wait for cleanup
            return CompilationResult(success=False, exit_code=-2)
        
    except FileNotFoundError:
        logger.warning("latexmk not found, falling back to direct compiler call")
        return _compile_latex_direct(str(tex_path), str(out_path), engine, max_runs)
    except Exception as e:
        logger.error(f"latexmk ({engine}) compilation failed: {e}")
        return CompilationResult(success=False, exit_code=-3)
    
    pdf_exists = pdf_path.exists()
    
    # Parse errors from log file
    error_count = 0
    errors = []
    quality_issue_count = 0
    quality_issues: List[str] = []
    quality_issue_severe = False
    if log_path.exists():
        error_count, errors = parse_log_errors(str(log_path))
        quality_issue_count, quality_issues, quality_issue_severe = parse_log_quality_issues(
            str(log_path),
            enable_quality_gate=True,
        )

    if (not pdf_exists) and error_count == 0:
        fallback_error = (
            f"{tex_filename}: compilation failed without parsable log errors "
            f"(exit code {last_exit_code})"
        )
        errors = [fallback_error]
        error_count = 1
    
    success = pdf_exists and error_count == 0
    
    logger.info(
        f"latexmk ({engine}) result: "
        f"PDF={'yes' if pdf_exists else 'no'}, "
        f"Errors={error_count}, "
        f"QualityIssues={quality_issue_count}, "
        f"Exit Code={last_exit_code}"
    )
    
    return CompilationResult(
        success=success,
        pdf_path=str(pdf_path) if pdf_exists else None,
        log_path=str(log_path) if log_path.exists() else None,
        error_count=error_count,
        errors=errors,
        exit_code=last_exit_code,
        quality_issue_count=quality_issue_count,
        quality_issues=quality_issues,
        quality_issue_severe=quality_issue_severe,
    )


async def compile_latex_async(
    tex_file: str,
    output_dir: str,
    engine: str = "pdflatex",
    max_runs: int = 2,
    *,
    on_process_start: Optional[Callable[[int, str], None]] = None,
    on_process_end: Optional[Callable[[], None]] = None,
    compilation_timeout: int = 300,
) -> CompilationResult:
    """
    Async variant of compile_latex() using asyncio subprocess primitives.
    """
    tex_path = Path(tex_file).resolve()
    out_path = Path(output_dir).resolve()

    if not tex_path.exists():
        logger.error(f"TeX file not found: {tex_file}")
        return CompilationResult(success=False, exit_code=-1)

    tex_filename = tex_path.name
    tex_basename = tex_path.stem
    out_path.mkdir(parents=True, exist_ok=True)
    pdf_path = out_path / f"{tex_basename}.pdf"
    log_path = out_path / f"{tex_basename}.log"
    _remove_stale_expected_pdf(pdf_path)

    logger.info(f"Compiling {tex_filename} with latexmk ({engine}) [async]...")
    last_exit_code = 0

    try:
        tex_dir = tex_path.parent
        has_real_bib = any(
            not bib.name.endswith("-blx.bib")
            for bib in Path(tex_dir).rglob("*.bib")
        )
        bibtex_flag = "-bibtex" if has_real_bib else "-bibtex-"
        logger.info(f"Bibliography detection: {'found' if has_real_bib else 'no'} .bib files -> using {bibtex_flag}")
        if not has_real_bib:
            _fallback_biblatex_to_thebibliography(str(tex_dir), str(out_path))

        cmd = [
            "latexmk",
            f"-{engine}",
            "-interaction=nonstopmode",
            f"-outdir={out_path}",
            "-file-line-error",
            "-synctex=1",
            bibtex_flag,
            tex_filename
        ]
        executor = _get_latex_executor()
        final_cmd = executor.prepare_command(cmd, tex_dir)

        proc: Optional[asyncio.subprocess.Process] = None
        try:
            proc = await _spawn_latex_process_async(final_cmd, tex_dir)
            if on_process_start and proc.pid:
                on_process_start(int(proc.pid), engine)
            await asyncio.wait_for(proc.communicate(), timeout=compilation_timeout)
            last_exit_code = int(proc.returncode or 0)
            logger.info(f"latexmk ({engine}) completed with exit code {last_exit_code}")
        except asyncio.TimeoutError:
            if proc is not None:
                logger.error(f"latexmk ({engine}) timed out after {compilation_timeout}s, terminating PID {proc.pid}")
                await _terminate_process_tree_and_wait(proc)
            return CompilationResult(success=False, exit_code=-2)
        except asyncio.CancelledError:
            if proc is not None:
                logger.info(f"latexmk ({engine}) cancelled, terminating PID {proc.pid}")
                await _terminate_process_tree_and_wait(proc)
            raise
        finally:
            if on_process_end:
                on_process_end()
    except FileNotFoundError:
        logger.warning("latexmk not found, falling back to direct compiler call (async)")
        return await _compile_latex_direct_async(
            str(tex_path),
            str(out_path),
            engine,
            max_runs,
            on_process_start=on_process_start,
            on_process_end=on_process_end,
        )
    except Exception as e:
        logger.error(f"latexmk ({engine}) compilation failed: {e}")
        return CompilationResult(success=False, exit_code=-3)

    pdf_exists = pdf_path.exists()
    error_count = 0
    errors: List[str] = []
    quality_issue_count = 0
    quality_issues: List[str] = []
    quality_issue_severe = False
    if log_path.exists():
        error_count, errors = parse_log_errors(str(log_path))
        quality_issue_count, quality_issues, quality_issue_severe = parse_log_quality_issues(
            str(log_path),
            enable_quality_gate=True,
        )

    if (not pdf_exists) and error_count == 0:
        errors = [f"{tex_filename}: compilation failed without parsable log errors (exit code {last_exit_code})"]
        error_count = 1

    success = pdf_exists and error_count == 0
    return CompilationResult(
        success=success,
        pdf_path=str(pdf_path) if pdf_exists else None,
        log_path=str(log_path) if log_path.exists() else None,
        error_count=error_count,
        errors=errors,
        exit_code=last_exit_code,
        quality_issue_count=quality_issue_count,
        quality_issues=quality_issues,
        quality_issue_severe=quality_issue_severe,
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
    tex_path = Path(tex_file).resolve()
    tex_filename = tex_path.name
    tex_basename = tex_path.stem
    out_path = Path(output_dir).resolve()
    out_path.mkdir(parents=True, exist_ok=True)
    pdf_path = out_path / f"{tex_basename}.pdf"
    log_path = out_path / f"{tex_basename}.log"
    _remove_stale_expected_pdf(pdf_path)
    
    logger.info(f"Compiling {tex_filename} directly with {engine}...")
    
    last_exit_code = 0
    executor = _get_latex_executor()
    is_host_executor = isinstance(executor, HostLatexExecutor)
    for run in range(max_runs):
        try:
            from backend.app.core.config import settings
            
            if is_host_executor and settings.latex_bin_dir and os.path.exists(settings.latex_bin_dir):
                engine_path = os.path.join(settings.latex_bin_dir, f"{engine}.exe")
                if not os.path.exists(engine_path):
                    logger.error(f"Compiler not found: {engine_path}")
                    return CompilationResult(success=False, exit_code=-3)
            else:
                engine_path = engine
            
            cmd = [
                engine_path,
                "-interaction=nonstopmode",
                # NOTE: -halt-on-error omitted - see compile_latex() for rationale.
                "-output-directory", str(out_path),
                tex_filename
            ]
            final_cmd = executor.prepare_command(cmd, tex_path.parent)
            
            # Use Popen for proper process tree cleanup on timeout
            direct_timeout = 300  # 5 minutes
            
            proc = subprocess.Popen(
                final_cmd,
                cwd=str(tex_path.parent),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            
            try:
                stdout, stderr = proc.communicate(timeout=direct_timeout)
                last_exit_code = proc.returncode
                logger.info(f"{engine} run {run + 1}/{max_runs} completed with exit code {proc.returncode}")
            except subprocess.TimeoutExpired:
                logger.error(f"{engine} compilation timed out, killing process tree (PID {proc.pid})...")
                _kill_process_tree(proc.pid)
                proc.wait(timeout=10)
                return CompilationResult(success=False, exit_code=-2)
            
        except Exception as e:
            logger.error(f"{engine} compilation failed: {e}")
            return CompilationResult(success=False, exit_code=-3)
    
    pdf_exists = pdf_path.exists()
    
    error_count = 0
    errors = []
    quality_issue_count = 0
    quality_issues: List[str] = []
    quality_issue_severe = False
    if log_path.exists():
        error_count, errors = parse_log_errors(str(log_path))
        quality_issue_count, quality_issues, quality_issue_severe = parse_log_quality_issues(
            str(log_path),
            enable_quality_gate=True,
        )

    if (not pdf_exists) and error_count == 0:
        fallback_error = (
            f"{tex_filename}: compilation failed without parsable log errors "
            f"(exit code {last_exit_code})"
        )
        errors = [fallback_error]
        error_count = 1
    
    success = pdf_exists and error_count == 0
    
    logger.info(
        f"{engine} compilation result: "
        f"PDF={'yes' if pdf_exists else 'no'}, "
        f"Errors={error_count}, "
        f"QualityIssues={quality_issue_count}, "
        f"Exit Code={last_exit_code}"
    )
    
    return CompilationResult(
        success=success,
        pdf_path=str(pdf_path) if pdf_exists else None,
        log_path=str(log_path) if log_path.exists() else None,
        error_count=error_count,
        errors=errors,
        exit_code=last_exit_code,
        quality_issue_count=quality_issue_count,
        quality_issues=quality_issues,
        quality_issue_severe=quality_issue_severe,
    )


async def _compile_latex_direct_async(
    tex_file: str,
    output_dir: str,
    engine: str = "pdflatex",
    max_runs: int = 2,
    *,
    on_process_start: Optional[Callable[[int, str], None]] = None,
    on_process_end: Optional[Callable[[], None]] = None,
    direct_timeout: int = 300,
) -> CompilationResult:
    tex_path = Path(tex_file).resolve()
    tex_filename = tex_path.name
    tex_basename = tex_path.stem
    out_path = Path(output_dir).resolve()
    out_path.mkdir(parents=True, exist_ok=True)
    pdf_path = out_path / f"{tex_basename}.pdf"
    log_path = out_path / f"{tex_basename}.log"
    _remove_stale_expected_pdf(pdf_path)

    last_exit_code = 0
    executor = _get_latex_executor()
    is_host_executor = isinstance(executor, HostLatexExecutor)
    for run in range(max_runs):
        proc: Optional[asyncio.subprocess.Process] = None
        try:
            from backend.app.core.config import settings

            if is_host_executor and settings.latex_bin_dir and os.path.exists(settings.latex_bin_dir):
                engine_path = os.path.join(settings.latex_bin_dir, f"{engine}.exe")
                if not os.path.exists(engine_path):
                    logger.error(f"Compiler not found: {engine_path}")
                    return CompilationResult(success=False, exit_code=-3)
            else:
                engine_path = engine

            cmd = [
                engine_path,
                "-interaction=nonstopmode",
                "-output-directory", str(out_path),
                tex_filename
            ]
            final_cmd = executor.prepare_command(cmd, tex_path.parent)
            proc = await _spawn_latex_process_async(final_cmd, tex_path.parent)
            if on_process_start and proc.pid:
                on_process_start(int(proc.pid), engine)
            try:
                await asyncio.wait_for(proc.communicate(), timeout=direct_timeout)
                last_exit_code = int(proc.returncode or 0)
            except asyncio.TimeoutError:
                await _terminate_process_tree_and_wait(proc)
                return CompilationResult(success=False, exit_code=-2)
            except asyncio.CancelledError:
                await _terminate_process_tree_and_wait(proc)
                raise
            finally:
                if on_process_end:
                    on_process_end()
        except Exception as e:
            logger.error(f"{engine} compilation failed: {e}")
            return CompilationResult(success=False, exit_code=-3)

    pdf_exists = pdf_path.exists()
    error_count = 0
    errors: List[str] = []
    quality_issue_count = 0
    quality_issues: List[str] = []
    quality_issue_severe = False
    if log_path.exists():
        error_count, errors = parse_log_errors(str(log_path))
        quality_issue_count, quality_issues, quality_issue_severe = parse_log_quality_issues(
            str(log_path),
            enable_quality_gate=True,
        )

    if (not pdf_exists) and error_count == 0:
        errors = [f"{tex_filename}: compilation failed without parsable log errors (exit code {last_exit_code})"]
        error_count = 1

    success = pdf_exists and error_count == 0
    return CompilationResult(
        success=success,
        pdf_path=str(pdf_path) if pdf_exists else None,
        log_path=str(log_path) if log_path.exists() else None,
        error_count=error_count,
        errors=errors,
        exit_code=last_exit_code,
        quality_issue_count=quality_issue_count,
        quality_issues=quality_issues,
        quality_issue_severe=quality_issue_severe,
    )


def _upgrade_outdated_cls_files(tex_dir: str) -> None:
    """
    Remove bundled .cls/.sty files that are outdated and conflict with the system TeX Live.
    
    Many arXiv submissions bundle old class files (e.g. IEEEtran.cls v1.8b from 2015).
    These can cause fatal compilation errors on newer TeX Live (e.g. 'Illegal parameter number').
    If a newer version exists in the system TeX Live, we remove the bundled copy so the
    system version is used instead.
    """
    # Known problematic class files and their minimum compatible versions
    # Format: filename -> (version_pattern_regex, min_year)
    KNOWN_PROBLEMATIC = {
        "IEEEtran.cls": 2020,  # v1.8b (2015) breaks on TeX Live 2024+
        "llncs.cls": 2020,     # Older LNCS class files can also break
    }
    
    tex_path = Path(tex_dir)
    
    for cls_file in tex_path.glob("*.cls"):
        filename = cls_file.name
        if filename not in KNOWN_PROBLEMATIC:
            continue
            
        min_year = KNOWN_PROBLEMATIC[filename]
        
        try:
            # Check if a system version exists via kpsewhich
            result = subprocess.run(
                ["kpsewhich", filename],
                capture_output=True, text=True, timeout=10
            )
            system_path = result.stdout.strip()
            
            if not system_path or not Path(system_path).exists():
                # No system version available, keep the bundled one
                continue
            
            # Read the bundled file to extract version date
            content = cls_file.read_text(encoding='utf-8', errors='ignore')[:5000]
            
            # Try to extract year from common version patterns
            # e.g. "2015/08/26", "2022/01/15", etc.
            year_match = re.search(r'(\d{4})/\d{2}/\d{2}', content)
            if year_match:
                file_year = int(year_match.group(1))
                if file_year < min_year:
                    logger.warning(
                        f"Removing outdated bundled {filename} (year={file_year}) - "
                        f"system has newer version at {system_path}"
                    )
                    cls_file.unlink()
                    continue
            
            # If we can't parse the year, compare file sizes as heuristic
            # System version is typically newer and larger
            bundled_size = cls_file.stat().st_size
            system_size = Path(system_path).stat().st_size
            if system_size > bundled_size * 1.1:  # System version is 10%+ larger
                logger.warning(
                    f"Removing bundled {filename} (size={bundled_size}B) - "
                    f"system version is larger ({system_size}B), likely newer"
                )
                cls_file.unlink()
                
        except Exception as e:
            logger.debug(f"Could not check {filename}: {e}")


_DOCUMENTCLASS_RE = re.compile(r'\\documentclass(?:\[[^\]]*\])?\{[^}]+\}')


def _inject_after_documentclass(tex_content: str, snippet: str) -> str:
    """Inject snippet right after \\documentclass when possible."""
    m = _DOCUMENTCLASS_RE.search(tex_content)
    if not m:
        return snippet + tex_content
    return tex_content[:m.end()] + snippet + tex_content[m.end():]


def _apply_engine_compat_shims(tex_content: str, engine: str, language: str) -> Tuple[str, List[str]]:
    """
    Apply deterministic engine-compatibility shims to tex content.

    Returns:
        (patched_content, [shim_name, ...])
    """
    patched = tex_content
    applied: List[str] = []

    if language == "cjk":
        if engine == "xelatex":
            swapped = re.sub(
                r'\\usepackage(?:\[[^\]]*\])?\{luatexja\}',
                r'\\usepackage{xeCJK}',
                patched,
            )
            if swapped != patched:
                patched = swapped
                applied.append("swap_luatexja_to_xeCJK")
        elif engine == "lualatex":
            swapped = re.sub(
                r'\\usepackage(?:\[[^\]]*\])?\{xeCJK\}',
                r'\\usepackage{luatexja}',
                patched,
            )
            if swapped != patched:
                patched = swapped
                applied.append("swap_xeCJK_to_luatexja")

    if engine in {"xelatex", "lualatex"}:
        # hwemoji is frequently incompatible with Xe/Lua environments in our runs.
        if re.search(r'\\usepackage(?:\[[^\]]*\])?\{hwemoji\}', patched):
            patched = re.sub(
                r'\\usepackage(?:\[[^\]]*\])?\{hwemoji\}',
                r'% \\usepackage{hwemoji} % disabled by engine compatibility shim',
                patched,
            )
            applied.append("disable_hwemoji_for_modern_engine")
            if r"\providecommand{\emoji}[1]{#1}" not in patched:
                patched = _inject_after_documentclass(
                    patched,
                    "\n\\providecommand{\\emoji}[1]{#1}\n",
                )
                applied.append("inject_emoji_fallback_macro")

        # Xe/Lua do not define pdfTeX primitives used by some templates.
        needs_pdftex_noop = (
            "\\pdfglyphtounicode" in patched or "\\pdfgentounicode" in patched
        )
        if needs_pdftex_noop and "\\providecommand{\\pdfglyphtounicode}[2]{}" not in patched:
            patched = _inject_after_documentclass(
                patched,
                "\n\\providecommand{\\pdfglyphtounicode}[2]{}\n"
                "\\providecommand{\\pdfgentounicode}[1]{}\n",
            )
            applied.append("inject_pdftex_primitive_noops")

    return patched, applied


def _decide_compiler_language(tex_file: str, target_language: Optional[str]) -> Tuple[str, str]:
    """
    Decide compiler language family and explain why.
    """
    target_mapped = map_target_language_to_family(target_language)
    if target_mapped:
        return target_mapped, f"target_language={target_language}->{target_mapped}"

    detected = detect_document_language(tex_file, include_inputs=True)
    return detected, "detected_from_main_and_includes"



def compile_with_intelligent_fallback(
    tex_file: str,
    output_dir: str,
    preferred_order: Optional[List[str]] = None,
    target_language: Optional[str] = None,
) -> Dict:
    """
    Intelligent LaTeX compilation with three-engine fallback strategy

    Strategy:
    1. Decide document language family from target language first, otherwise auto-detect.
    2. Build engine order from language family or user override.
    3. Apply deterministic compatibility shims per engine.
    4. Try each engine in order and pick the best successful PDF.
    """
    logger.info(f"Starting intelligent three-engine compilation for {tex_file}")

    normalized_tex_file = str(Path(tex_file).resolve())
    normalized_output_dir = str(Path(output_dir).resolve())
    tex_dir = str(Path(normalized_tex_file).parent)

    language, language_reason = _decide_compiler_language(normalized_tex_file, target_language)
    mapped_target_language = map_target_language_to_family(target_language)
    language_decision: Dict[str, Any] = {
        "target_language": target_language,
        "target_language_family": mapped_target_language,
        "resolved_language": language,
        "reason": language_reason,
        "detection_scope": (
            "target_language_override"
            if mapped_target_language is not None
            else "main_and_includes"
        ),
    }

    engine_order_notes: List[str] = []
    if preferred_order is not None:
        engines = list(preferred_order)
        engine_order_notes.append(f"preferred_order_override={engines}")
    else:
        if language == "cjk":
            engines = ["xelatex", "lualatex"]
            engine_order_notes.append("language_family=cjk_default_order")
        elif language == "cyrillic":
            engines = ["xelatex", "lualatex", "pdflatex"]
            engine_order_notes.append("language_family=cyrillic_default_order")
        else:
            engines = ["pdflatex", "xelatex", "lualatex"]
            engine_order_notes.append("language_family=latin_default_order")

    # De-duplicate while preserving first occurrence.
    ordered_unique_engines: List[str] = []
    for candidate in engines:
        if candidate not in ordered_unique_engines:
            ordered_unique_engines.append(candidate)
    engines = ordered_unique_engines

    # Package-aware engine selection:
    # - keep Xe priority when luatexja is present;
    # - skip lualatex for xypdf incompatibility.
    try:
        tex_content_for_pkg_scan = _remove_comments(
            collect_detection_content(normalized_tex_file, 50_000)
        )
        if re.search(r'\\usepackage(?:\[[^\]]*\])?\{luatexja\}', tex_content_for_pkg_scan):
            if "xelatex" in engines:
                engines = ["xelatex"] + [e for e in engines if e != "xelatex"]
                engine_order_notes.append("luatexja_detected_keep_xelatex_priority")
        if re.search(r'\\usepackage(?:\[[^\]]*\])?\{xypdf\}', tex_content_for_pkg_scan):
            if "lualatex" in engines:
                engines = [e for e in engines if e != "lualatex"]
                engine_order_notes.append("xypdf_detected_skip_lualatex")
    except Exception as scan_err:
        logger.debug("Package-aware engine scan failed (non-fatal): %s", scan_err)
        engine_order_notes.append("package_scan_failed_non_fatal")

    engine_order_reason = "; ".join(engine_order_notes) if engine_order_notes else "default"
    logger.info(
        "Compiler language decision=%s, engine_order=%s, reason=%s",
        language,
        engines,
        engine_order_reason,
    )

    compat_shims_applied: List[Dict[str, Any]] = []

    # ---------------------------------------------------------------------------
    # STAGE 0: Pre-Compile Sanitization (Incompatible Package Filtering)
    # ---------------------------------------------------------------------------
    # Scans and comments out packages known to crash modern engines in CJK mode.
    # ---------------------------------------------------------------------------
    precompile_warnings: List[str] = []
    if language == "cjk":
        logger.info("Stage 0 (pre-compile): scanning all .tex files for incompatible packages...")
        for tex_path in list(Path(tex_dir).rglob("*.tex")):
            try:
                content = tex_path.read_text(encoding="utf-8", errors="replace")
                sanitizer_output, round_warnings = apply_precompile_sanitization(content)
                if round_warnings:
                    tex_path.write_text(sanitizer_output, encoding="utf-8")
                    precompile_warnings.extend(round_warnings)
                    logger.info("Stage 0: sanitized %s (%d package(s) filtered)", tex_path.name, len(round_warnings))
            except Exception as e:
                logger.warning("Stage 0: failed to process %s: %s", tex_path.name, e)

    def _with_diagnostics(payload: Dict[str, Any]) -> Dict[str, Any]:
        payload = dict(payload)
        payload["language_decision"] = language_decision
        payload["engine_order_reason"] = engine_order_reason
        payload["compat_shims_applied"] = compat_shims_applied

        # Merge Stage 0 (Pre-compile) warnings if they exist
        if precompile_warnings:
            existing_warnings = payload.get("warnings")
            prefix = "[Stage 0: Pre-compile Sanitization] " + "; ".join(precompile_warnings)
            if existing_warnings:
                payload["warnings"] = prefix + " | " + str(existing_warnings)
            else:
                payload["warnings"] = prefix
        return payload

    tex_path_obj = Path(normalized_tex_file)
    original_tex_content: Optional[str] = None
    try:
        original_tex_content = tex_path_obj.read_text(encoding="utf-8", errors="replace")
    except Exception as read_err:
        logger.warning("Failed to read source tex for compatibility shims: %s", read_err)

    # ---------------------------------------------------------------------------
    # Tiered Compilation Strategy (OpenSpec: tiered-compilation)
    # ---------------------------------------------------------------------------
    # Stage 0 – Pristine:  attempt every engine as-is, no source modifications.
    # Stage 1 – Shimmed:   apply engine-compat shims but do NOT delete .cls files.
    # Stage 2 – Invasive:  call _upgrade_outdated_cls_files + biblatex fallback.
    #                       Only reached when both Stage 0 and Stage 1 fail.
    # ---------------------------------------------------------------------------

    # Collect results from all engines, keyed by (stage, engine).
    results: Dict[str, CompilationResult] = {}

    def _clean_aux_files():
        """Clean engine-specific auxiliary files from previous runs."""
        for ext in [".out", ".toc", ".fls", ".fdb_latexmk", ".xdv", ".nav", ".snm"]:
            aux_file = Path(normalized_output_dir) / f"{Path(normalized_tex_file).stem}{ext}"
            if aux_file.exists():
                try:
                    aux_file.unlink()
                except OSError:
                    pass

    def _preserve_pdf_and_log(
        result: CompilationResult, engine: str, stage_label: str
    ) -> CompilationResult:
        """Copy engine PDF/log to a stable snapshot file and update result paths."""
        if result.pdf_path:
            pdf_candidate = Path(result.pdf_path)
            if pdf_candidate.exists():
                preserved_pdf = (
                    Path(normalized_output_dir)
                    / f"{Path(normalized_tex_file).stem}.{engine}.{stage_label}.pdf"
                )
                try:
                    shutil.copy2(pdf_candidate, preserved_pdf)
                    result.pdf_path = str(preserved_pdf)
                    logger.info(f"Preserved {engine} ({stage_label}) PDF snapshot: {preserved_pdf}")
                    if result.log_path:
                        log_candidate = Path(result.log_path)
                        if log_candidate.exists():
                            preserved_log = (
                                Path(normalized_output_dir)
                                / f"{Path(normalized_tex_file).stem}_{engine}_{stage_label}.log"
                            )
                            try:
                                shutil.copy2(log_candidate, preserved_log)
                            except Exception:
                                pass
                except Exception as exc:
                    logger.warning(f"Failed to preserve {engine} PDF snapshot: {exc}")
                    result.pdf_path = str(pdf_candidate) if pdf_candidate.exists() else None
            else:
                logger.warning(f"Engine {engine} returned a non-existent PDF path: {pdf_candidate}")
                result.pdf_path = None
        return result

    def _is_perfect(result: CompilationResult) -> bool:
        """Return True iff the compilation is error-free (and CJK quality-OK)."""
        effective_quality = result.quality_issue_count if language == "cjk" else 0
        return result.success and result.error_count == 0 and effective_quality == 0

    try:
        # ------------------------------------------------------------------ #
        # STAGE 0: Pristine — no modifications to user source whatsoever.      #
        # ------------------------------------------------------------------ #
        logger.info("Stage 0 (pristine): attempting compilation without source modifications.")
        for engine in engines:
            _clean_aux_files()
            logger.info(f"Stage 0 – attempting engine {engine}...")
            result = compile_latex(normalized_tex_file, normalized_output_dir, engine=engine)
            result = _preserve_pdf_and_log(result, engine, "stage0")
            compat_shims_applied.append({"engine": engine, "stage": 0, "shims": []})
            results[f"stage0_{engine}"] = result
            if _is_perfect(result):
                if language == "cjk" and engine == "pdflatex":
                    logger.debug("Stage 0 pdflatex perfect for CJK; still trying modern engines")
                else:
                    logger.info(f"Stage 0: {engine} produced perfect compilation.")
                    return _with_diagnostics(
                        {
                            "pdf_path": result.pdf_path,
                            "status": "completed",
                            "engine": engine,
                            "error_count": 0,
                            "warnings": None,
                            "errors": None,
                        }
                    )

        # ------------------------------------------------------------------ #
        # STAGE 1: Shimmed — apply engine compatibility shims, no .cls delete. #
        # ------------------------------------------------------------------ #
        logger.info(
            "Stage 0 did not produce a perfect result. "
            "Stage 1 (shimmed): applying engine compatibility shims."
        )
        for engine in engines:
            if original_tex_content is None:
                applied_shims_list: List[str] = ["skip_shims_source_unreadable"]
            else:
                patched_tex_content, applied_shims_list = _apply_engine_compat_shims(
                    original_tex_content, engine, language
                )
                if patched_tex_content != original_tex_content:
                    try:
                        tex_path_obj.write_text(patched_tex_content, encoding="utf-8")
                    except Exception as write_err:
                        logger.warning(
                            "Stage 1: failed to write shimmed TeX for engine %s: %s", engine, write_err
                        )
                        applied_shims_list = list(applied_shims_list) + ["shim_write_failed"]
                else:
                    # No shims needed for this engine; skip to avoid re-running same compile.
                    logger.debug(f"Stage 1: no shims for {engine}, skipping.")
                    continue

            _clean_aux_files()
            compat_shims_applied.append({"engine": engine, "stage": 1, "shims": applied_shims_list})
            if applied_shims_list:
                logger.info("Stage 1 – applied shims for %s: %s", engine, applied_shims_list)
            logger.info(f"Stage 1 – attempting engine {engine}...")
            result = compile_latex(normalized_tex_file, normalized_output_dir, engine=engine)
            result = _preserve_pdf_and_log(result, engine, "stage1")
            results[f"stage1_{engine}"] = result
            if _is_perfect(result):
                if language == "cjk" and engine == "pdflatex":
                    logger.debug("Stage 1 pdflatex perfect for CJK; still trying modern engines")
                else:
                    logger.info(f"Stage 1 (shimmed): {engine} produced perfect compilation.")
                    return _with_diagnostics(
                        {
                            "pdf_path": result.pdf_path,
                            "status": "completed",
                            "engine": engine,
                            "error_count": 0,
                            "warnings": None,
                            "errors": None,
                        }
                    )

        # ------------------------------------------------------------------ #
        # STAGE 2: Invasive — upgrade cls files + biblatex fallback.           #
        # Only reached when Stage 0 and Stage 1 produced no perfect result.   #
        # ------------------------------------------------------------------ #
        logger.warning(
            "Stage 0 and Stage 1 did not produce a perfect result. "
            "Stage 2 (invasive): upgrading cls files and running biblatex fallback."
        )
        _upgrade_outdated_cls_files(tex_dir)
        compat_shims_applied.append({"engine": "*", "stage": 2, "shims": ["upgrade_cls_files"]})

        for engine in engines:
            if original_tex_content is None:
                applied_shims_list = ["skip_shims_source_unreadable"]
            else:
                patched_tex_content, applied_shims_list = _apply_engine_compat_shims(
                    original_tex_content, engine, language
                )
                try:
                    tex_path_obj.write_text(patched_tex_content, encoding="utf-8")
                except Exception as write_err:
                    logger.warning(
                        "Stage 2: failed to write shimmed TeX for engine %s: %s", engine, write_err
                    )
                    applied_shims_list = list(applied_shims_list) + ["shim_write_failed"]

            _clean_aux_files()
            compat_shims_applied.append({"engine": engine, "stage": 2, "shims": applied_shims_list})
            logger.info(f"Stage 2 – attempting engine {engine}...")
            result = compile_latex(normalized_tex_file, normalized_output_dir, engine=engine)
            result = _preserve_pdf_and_log(result, engine, "stage2")
            results[f"stage2_{engine}"] = result
            if _is_perfect(result):
                if language == "cjk" and engine == "pdflatex":
                    logger.debug("Stage 2 pdflatex perfect for CJK; continuing for merit selection")
                else:
                    logger.info(f"Stage 2 (invasive): {engine} produced perfect compilation (DEGRADED).")
                    return _with_diagnostics(
                        {
                            "pdf_path": result.pdf_path,
                            "status": "completed",
                            "engine": engine,
                            "error_count": 0,
                            "warnings": "Stage 2 (invasive) was used: user .cls files may have been modified.",
                            "errors": None,
                        }
                    )

        # All three stages and all engines have been exhausted.
        # Fall through to best-effort selection on whatever PDFs we have.
        engine_result_items = [
            (k.split("_", 1)[1], v) for k, v in results.items()
        ]  # strip stage prefix

        # Build a deduplicated (engine, result) list preferring later stages.
        dedup: Dict[str, CompilationResult] = {}
        for eng, res in engine_result_items:
            if eng not in dedup or (dedup[eng].pdf_path is None and res.pdf_path is not None):
                dedup[eng] = res
        # Use this for best-effort selection below.
        result_items_for_selection = list(dedup.items())
        result_items_for_selection_with_pdf = [
            (eng, res)
            for eng, res in result_items_for_selection
            if res.pdf_path is not None and Path(res.pdf_path).exists()
        ]

        # Also expose the raw per-engine results on the path the old code used.
        for eng, res in dedup.items():
            results[eng] = res

            # Preserve each engine PDF under an engine-specific filename.
            if result.pdf_path:
                pdf_candidate = Path(result.pdf_path)
                if pdf_candidate.exists():
                    preserved_pdf = Path(normalized_output_dir) / f"{Path(normalized_tex_file).stem}.{engine}.pdf"
                    try:
                        shutil.copy2(pdf_candidate, preserved_pdf)
                        result.pdf_path = str(preserved_pdf)
                        logger.info(f"Preserved {engine} PDF snapshot: {preserved_pdf}")

                        # Preserve each engine LOG snapshot for observability.
                        if result.log_path:
                            log_candidate = Path(result.log_path)
                            if log_candidate.exists():
                                preserved_log = Path(normalized_output_dir) / f"{Path(normalized_tex_file).stem}_{engine}.log"
                                try:
                                    shutil.copy2(log_candidate, preserved_log)
                                    logger.info(f"Preserved {engine} LOG snapshot: {preserved_log}")
                                except Exception as exc:
                                    logger.warning(f"Failed to preserve {engine} LOG snapshot: {exc}")
                    except Exception as exc:
                        logger.warning(
                            f"Failed to preserve {engine} PDF snapshot from {pdf_candidate}: {exc}"
                        )
                        result.pdf_path = str(pdf_candidate) if pdf_candidate.exists() else None
                else:
                    logger.warning(
                        f"Engine {engine} returned a non-existent PDF path: {pdf_candidate}"
                    )
                    result.pdf_path = None

            results[engine] = result

            effective_quality_issue_count = result.quality_issue_count if language == "cjk" else 0

            # Perfect compilation: no hard errors and no CJK quality issues.
            if result.success and result.error_count == 0 and effective_quality_issue_count == 0:
                if language == "cjk" and engine == "pdflatex":
                    logger.debug("pdflatex produced 0 errors for CJK; continuing for merit selection")
                else:
                    logger.info(f"{engine} produced perfect compilation (zero errors)")
                    return _with_diagnostics(
                        {
                            "pdf_path": result.pdf_path,
                            "status": "completed",
                            "engine": engine,
                            "error_count": 0,
                            "warnings": None,
                            "errors": None,
                        }
                    )

        # -------------------------------------------------------------------
        # STAGE 3: Iterative Image Sanitizer
        #
        # Triggered when image-related errors appear in ANY engine log.
        # Invariants:
        #   A) Compilation-failure driven — never runs when compilation succeeded.
        #   B) Original files are never modified (Ghostscript writes *.sanitized.pdf).
        #   C) Monotonic convergence — sanitized_files only grows; each PDF is
        #      distilled at most once; loop exits immediately when no new files
        #      are discovered.
        # -------------------------------------------------------------------
        all_error_lines: List[str] = []
        for res in dedup.values():
            all_error_lines.extend(res.errors)

        _IMAGE_TRIGGERS = ("reading image failed", "pdf inclusion")
        if any(any(kw in ln.lower() for kw in _IMAGE_TRIGGERS) for ln in all_error_lines):
            logger.warning(
                "Stage 3 (image sanitizer): detected PDF inclusion errors — "
                "entering iterative repair loop (max %d rounds).",
                MAX_SANITIZE_ROUNDS,
            )

            # Accumulated set of original PDF paths that have been repaired
            # across all rounds.  Grows monotonically; never shrinks.
            sanitized_files: set = set()
            # All sanitized *output* paths for the final warning message.
            all_sanitized_outputs: List[Path] = []

            # Pick the best engine from Stage 2: prefer the one with fewest errors
            # that produced a PDF; fall back to whichever engine ran last.
            best_s2_engine = engines[-1]
            if result_items_for_selection_with_pdf:
                best_s2_engine = min(
                    result_items_for_selection_with_pdf,
                    key=lambda x: x[1].error_count,
                )[0]
            elif result_items_for_selection:
                best_s2_engine = min(
                    result_items_for_selection,
                    key=lambda x: x[1].error_count,
                )[0]

            # The error lines to scan at the start of each round (seeded with
            # Stage 2 errors; updated with each round's compilation result).
            round_error_lines = all_error_lines
            current_round_result: Optional[CompilationResult] = None

            for round_idx in range(MAX_SANITIZE_ROUNDS):
                # Short-circuit A: no image errors in this round's log.
                has_image_error = any(
                    any(kw in ln.lower() for kw in _IMAGE_TRIGGERS)
                    for ln in round_error_lines
                )
                if not has_image_error:
                    logger.info(
                        "Stage 3 round %d: no image errors detected; exiting loop.",
                        round_idx,
                    )
                    break

                newly_sanitized_outputs, any_new, newly_sanitized_originals = try_sanitize_images_in_errors(
                    round_error_lines,
                    Path(tex_dir),
                    already_sanitized=sanitized_files,
                )

                # Short-circuit B: all detected bad PDFs were already repaired.
                if not any_new:
                    logger.info(
                        "Stage 3 round %d: no new corrupted PDFs discovered (short-circuit).",
                        round_idx,
                    )
                    break

                # Merge newly repaired files into the global accumulator.
                sanitized_files.update(newly_sanitized_originals)
                all_sanitized_outputs.extend(newly_sanitized_outputs)
                logger.info(
                    "Stage 3 round %d: repaired %d new PDF(s) — cumulative total %d.",
                    round_idx,
                    len(newly_sanitized_originals),
                    len(sanitized_files),
                )

                # Recompile with the best single engine.
                _clean_aux_files()
                logger.info(
                    "Stage 3 round %d — retrying engine %s after image sanitization...",
                    round_idx,
                    best_s2_engine,
                )
                current_round_result = compile_latex(
                    normalized_tex_file, normalized_output_dir, engine=best_s2_engine
                )
                current_round_result = _preserve_pdf_and_log(
                    current_round_result, best_s2_engine, f"stage3_r{round_idx}"
                )
                results[f"stage3_r{round_idx}_{best_s2_engine}"] = current_round_result

                if _is_perfect(current_round_result):
                    logger.info(
                        "Stage 3 round %d: %s produced perfect compilation.",
                        round_idx, best_s2_engine,
                    )
                    return _with_diagnostics(
                        {
                            "pdf_path": current_round_result.pdf_path,
                            "status": "completed_with_warnings",
                            "engine": best_s2_engine,
                            "error_count": 0,
                            "warnings": (
                                f"Stage 3 (image sanitizer) repaired "
                                f"{len(all_sanitized_outputs)} corrupted PDF image(s) "
                                f"across {round_idx + 1} round(s): "
                                + ", ".join(p.name for p in all_sanitized_outputs)
                            ),
                            "errors": None,
                        }
                    )

                if (
                    current_round_result.pdf_path
                    and current_round_result.error_count < sum(
                        res.error_count for res in dedup.values()
                    )
                ):
                    logger.info(
                        "Stage 3 round %d: %s reduced errors; accepting best-effort PDF.",
                        round_idx, best_s2_engine,
                    )
                    return _with_diagnostics(
                        {
                            "pdf_path": current_round_result.pdf_path,
                            "status": "completed_with_warnings",
                            "engine": best_s2_engine,
                            "error_count": current_round_result.error_count,
                            "warnings": (
                                f"Stage 3 (image sanitizer) partially repaired "
                                f"{len(all_sanitized_outputs)} image(s) across "
                                f"{round_idx + 1} round(s). "
                                f"{current_round_result.error_count} residual error(s)."
                            ),
                            "errors": None,
                        }
                    )

                # Feed this round's errors into the next round.
                round_error_lines = current_round_result.errors


        # -------------------------------------------------------------------
        # Best-effort fallback: if Stage 3 didn't succeed (or wasn't needed),
        # return the PDF with fewest errors produced by any stage 0-2 engine.
        # -------------------------------------------------------------------
        engines_with_pdf = result_items_for_selection_with_pdf

        # CJK specific: Exclude pdflatex result if modern engines yielded a PDF.
        if language == "cjk":
            modern_engines_with_pdf = [
                (e, r) for e, r in engines_with_pdf if e in ["xelatex", "lualatex"]
            ]
            if modern_engines_with_pdf:
                logger.info("Found modern-engine PDFs for CJK; excluding pdflatex result.")
                engines_with_pdf = modern_engines_with_pdf

        if engines_with_pdf:
            engines_with_pdf.sort(
                key=lambda x: (
                    x[1].error_count,
                    x[1].quality_issue_count if language == "cjk" else 0,
                )
            )
            best_engine, best_result = engines_with_pdf[0]

            if language == "cjk":
                comparison = ", ".join(
                    f"{eng}: errors={res.error_count}, quality={res.quality_issue_count}"
                    for eng, res in dedup.items()
                )
            else:
                comparison = ", ".join(
                    f"{eng}: {res.error_count}" for eng, res in dedup.items()
                )

            logger.warning(
                f"Selected {best_engine} PDF with {best_result.error_count} errors ({comparison})"
            )

            warning_msg = f"Compilation completed with {best_result.error_count} errors using {best_engine}."
            if language == "cjk" and best_result.quality_issue_count > 0:
                warning_msg += (
                    f" Detected {best_result.quality_issue_count} CJK missing-character "
                    "quality issues in the chosen engine log."
                )

            return _with_diagnostics(
                {
                    "pdf_path": best_result.pdf_path,
                    "status": "completed_with_warnings",
                    "engine": best_engine,
                    "error_count": best_result.error_count,
                    "warnings": warning_msg,
                    "errors": None,
                }
            )

        # All engines and all stages (including image sanitizer) failed.

        logger.error(f"All stages and engines failed to produce PDF: {engines}")

        combined_errors = "Compilation failed with all engines across all stages:\n\n"
        for eng, res in dedup.items():
            combined_errors += f"{eng} ({res.error_count} errors):\n"
            combined_errors += "\n".join(res.errors[:10]) + "\n\n"

        total_errors = sum(res.error_count for res in dedup.values())
        return _with_diagnostics(
            {
                "pdf_path": None,
                "status": "failed_compilation",
                "engine": None,
                "error_count": total_errors,
                "warnings": None,
                "errors": combined_errors,
            }
        )
    finally:
        if original_tex_content is not None:
            try:
                tex_path_obj.write_text(original_tex_content, encoding="utf-8")
            except Exception as restore_err:
                logger.warning("Failed to restore original TeX source after fallback compile: %s", restore_err)


def compile_with_fallback(tex_file: str, output_dir: str) -> Dict:
    """
    Intelligent LaTeX compilation with fallback strategy (backward compatible)
    
    This function is kept for backward compatibility.
    It now delegates to compile_with_intelligent_fallback.
    
    Strategy:
    1. Auto-detect document language
    2. For CJK: XeLaTeX -> LuaLaTeX -> PDFLaTeX
    3. For Latin: PDFLaTeX -> XeLaTeX -> LuaLaTeX
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
        logger.info("pdflatex produced perfect compilation (zero errors)")
        return {
            "pdf_path": pdflatex_result.pdf_path,
            "status": "completed",
            "engine": "pdflatex",
            "error_count": 0,
            "warnings": None,
            "errors": None
        }
    
    # Step 2: Try xelatex fallback
    logger.info("Attempting xelatex fallback...")
    xelatex_result = compile_latex(tex_file, output_dir, engine="xelatex")
    
    # Perfect xelatex compilation
    if xelatex_result.success and xelatex_result.error_count == 0:
        logger.info("xelatex produced perfect compilation (zero errors)")
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
        logger.warning(f"Only pdflatex produced PDF (with {pdflatex_result.error_count} errors)")
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
        logger.warning(f"Only xelatex produced PDF (with {xelatex_result.error_count} errors)")
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
            f"Selected {engine} PDF with {result.error_count} errors "
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
    logger.error("Both pdflatex and xelatex failed to produce PDF")
    
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


async def compile_with_intelligent_fallback_async(
    tex_file: str,
    output_dir: str,
    preferred_order: Optional[List[str]] = None,
    target_language: Optional[str] = None,
    *,
    on_process_start: Optional[Callable[[int, str], None]] = None,
    on_process_end: Optional[Callable[[], None]] = None,
) -> Dict[str, Any]:
    """
    Async intelligent fallback with the same stage/selection semantics as the
    synchronous implementation, while using non-blocking subprocess awaits.
    """
    from backend.app.core.config import settings

    # Rollback switch: keep legacy path available.
    if not bool(getattr(settings, "async_compiler_enabled", True)):
        return await asyncio.to_thread(
            compile_with_intelligent_fallback,
            tex_file,
            output_dir,
            preferred_order,
            target_language,
        )

    logger.info(f"Starting intelligent three-engine compilation for {tex_file} [async]")

    normalized_tex_file = str(Path(tex_file).resolve())
    normalized_output_dir = str(Path(output_dir).resolve())
    tex_dir = str(Path(normalized_tex_file).parent)

    language, language_reason = _decide_compiler_language(normalized_tex_file, target_language)
    mapped_target_language = map_target_language_to_family(target_language)
    language_decision: Dict[str, Any] = {
        "target_language": target_language,
        "target_language_family": mapped_target_language,
        "resolved_language": language,
        "reason": language_reason,
        "detection_scope": (
            "target_language_override"
            if mapped_target_language is not None
            else "main_and_includes"
        ),
    }

    engine_order_notes: List[str] = []
    if preferred_order is not None:
        engines = list(preferred_order)
        engine_order_notes.append(f"preferred_order_override={engines}")
    else:
        if language == "cjk":
            engines = ["xelatex", "lualatex"]
            engine_order_notes.append("language_family=cjk_default_order")
        elif language == "cyrillic":
            engines = ["xelatex", "lualatex", "pdflatex"]
            engine_order_notes.append("language_family=cyrillic_default_order")
        else:
            engines = ["pdflatex", "xelatex", "lualatex"]
            engine_order_notes.append("language_family=latin_default_order")

    ordered_unique_engines: List[str] = []
    for candidate in engines:
        if candidate not in ordered_unique_engines:
            ordered_unique_engines.append(candidate)
    engines = ordered_unique_engines

    try:
        tex_content_for_pkg_scan = _remove_comments(
            collect_detection_content(normalized_tex_file, 50_000)
        )
        if re.search(r'\\usepackage(?:\[[^\]]*\])?\{luatexja\}', tex_content_for_pkg_scan):
            if "xelatex" in engines:
                engines = ["xelatex"] + [e for e in engines if e != "xelatex"]
                engine_order_notes.append("luatexja_detected_keep_xelatex_priority")
        if re.search(r'\\usepackage(?:\[[^\]]*\])?\{xypdf\}', tex_content_for_pkg_scan):
            if "lualatex" in engines:
                engines = [e for e in engines if e != "lualatex"]
                engine_order_notes.append("xypdf_detected_skip_lualatex")
    except Exception as scan_err:
        logger.debug("Package-aware engine scan failed (non-fatal): %s", scan_err)
        engine_order_notes.append("package_scan_failed_non_fatal")

    engine_order_reason = "; ".join(engine_order_notes) if engine_order_notes else "default"
    logger.info(
        "Compiler language decision=%s, engine_order=%s, reason=%s",
        language,
        engines,
        engine_order_reason,
    )

    compat_shims_applied: List[Dict[str, Any]] = []
    precompile_warnings: List[str] = []
    if language == "cjk":
        logger.info("Stage 0 (pre-compile): scanning all .tex files for incompatible packages...")
        for tex_path in list(Path(tex_dir).rglob("*.tex")):
            try:
                content = tex_path.read_text(encoding="utf-8", errors="replace")
                sanitizer_output, round_warnings = apply_precompile_sanitization(content)
                if round_warnings:
                    tex_path.write_text(sanitizer_output, encoding="utf-8")
                    precompile_warnings.extend(round_warnings)
                    logger.info("Stage 0: sanitized %s (%d package(s) filtered)", tex_path.name, len(round_warnings))
            except Exception as e:
                logger.warning("Stage 0: failed to process %s: %s", tex_path.name, e)

    def _with_diagnostics(payload: Dict[str, Any]) -> Dict[str, Any]:
        payload = dict(payload)
        payload["language_decision"] = language_decision
        payload["engine_order_reason"] = engine_order_reason
        payload["compat_shims_applied"] = compat_shims_applied
        if precompile_warnings:
            existing_warnings = payload.get("warnings")
            prefix = "[Stage 0: Pre-compile Sanitization] " + "; ".join(precompile_warnings)
            payload["warnings"] = prefix if not existing_warnings else f"{prefix} | {existing_warnings}"
        return payload

    tex_path_obj = Path(normalized_tex_file)
    original_tex_content: Optional[str] = None
    try:
        original_tex_content = tex_path_obj.read_text(encoding="utf-8", errors="replace")
    except Exception as read_err:
        logger.warning("Failed to read source tex for compatibility shims: %s", read_err)

    results: Dict[str, CompilationResult] = {}

    def _clean_aux_files() -> None:
        for ext in [".out", ".toc", ".fls", ".fdb_latexmk", ".xdv", ".nav", ".snm"]:
            aux_file = Path(normalized_output_dir) / f"{Path(normalized_tex_file).stem}{ext}"
            if aux_file.exists():
                try:
                    aux_file.unlink()
                except OSError:
                    pass

    def _preserve_pdf_and_log(result: CompilationResult, engine: str, stage_label: str) -> CompilationResult:
        if result.pdf_path:
            pdf_candidate = Path(result.pdf_path)
            if pdf_candidate.exists():
                preserved_pdf = Path(normalized_output_dir) / f"{Path(normalized_tex_file).stem}.{engine}.{stage_label}.pdf"
                try:
                    shutil.copy2(pdf_candidate, preserved_pdf)
                    result.pdf_path = str(preserved_pdf)
                    logger.info(f"Preserved {engine} ({stage_label}) PDF snapshot: {preserved_pdf}")
                    if result.log_path:
                        log_candidate = Path(result.log_path)
                        if log_candidate.exists():
                            preserved_log = Path(normalized_output_dir) / f"{Path(normalized_tex_file).stem}_{engine}_{stage_label}.log"
                            try:
                                shutil.copy2(log_candidate, preserved_log)
                            except Exception:
                                pass
                except Exception as exc:
                    logger.warning(f"Failed to preserve {engine} PDF snapshot: {exc}")
                    result.pdf_path = str(pdf_candidate) if pdf_candidate.exists() else None
            else:
                logger.warning(f"Engine {engine} returned a non-existent PDF path: {pdf_candidate}")
                result.pdf_path = None
        return result

    def _is_perfect(result: CompilationResult) -> bool:
        effective_quality = result.quality_issue_count if language == "cjk" else 0
        return result.success and result.error_count == 0 and effective_quality == 0

    async def _compile_one(engine: str) -> CompilationResult:
        return await compile_latex_async(
            normalized_tex_file,
            normalized_output_dir,
            engine=engine,
            on_process_start=on_process_start,
            on_process_end=on_process_end,
        )

    try:
        logger.info("Stage 0 (pristine): attempting compilation without source modifications.")
        for engine in engines:
            _clean_aux_files()
            logger.info(f"Stage 0 - attempting engine {engine}...")
            result = await _compile_one(engine)
            result = _preserve_pdf_and_log(result, engine, "stage0")
            compat_shims_applied.append({"engine": engine, "stage": 0, "shims": []})
            results[f"stage0_{engine}"] = result
            if _is_perfect(result):
                if language == "cjk" and engine == "pdflatex":
                    logger.debug("Stage 0 pdflatex perfect for CJK; still trying modern engines")
                else:
                    logger.info(f"Stage 0: {engine} produced perfect compilation.")
                    return _with_diagnostics(
                        {
                            "pdf_path": result.pdf_path,
                            "status": "completed",
                            "engine": engine,
                            "error_count": 0,
                            "warnings": None,
                            "errors": None,
                        }
                    )

        logger.info("Stage 0 did not produce a perfect result. Stage 1 (shimmed): applying engine compatibility shims.")
        for engine in engines:
            if original_tex_content is None:
                applied_shims_list: List[str] = ["skip_shims_source_unreadable"]
            else:
                patched_tex_content, applied_shims_list = _apply_engine_compat_shims(
                    original_tex_content, engine, language
                )
                if patched_tex_content != original_tex_content:
                    try:
                        tex_path_obj.write_text(patched_tex_content, encoding="utf-8")
                    except Exception as write_err:
                        logger.warning("Stage 1: failed to write shimmed TeX for engine %s: %s", engine, write_err)
                        applied_shims_list = list(applied_shims_list) + ["shim_write_failed"]
                else:
                    logger.debug(f"Stage 1: no shims for {engine}, skipping.")
                    continue

            _clean_aux_files()
            compat_shims_applied.append({"engine": engine, "stage": 1, "shims": applied_shims_list})
            if applied_shims_list:
                logger.info("Stage 1 - applied shims for %s: %s", engine, applied_shims_list)
            logger.info(f"Stage 1 - attempting engine {engine}...")
            result = await _compile_one(engine)
            result = _preserve_pdf_and_log(result, engine, "stage1")
            results[f"stage1_{engine}"] = result
            if _is_perfect(result):
                if language == "cjk" and engine == "pdflatex":
                    logger.debug("Stage 1 pdflatex perfect for CJK; still trying modern engines")
                else:
                    logger.info(f"Stage 1 (shimmed): {engine} produced perfect compilation.")
                    return _with_diagnostics(
                        {
                            "pdf_path": result.pdf_path,
                            "status": "completed",
                            "engine": engine,
                            "error_count": 0,
                            "warnings": None,
                            "errors": None,
                        }
                    )

        logger.warning(
            "Stage 0 and Stage 1 did not produce a perfect result. Stage 2 (invasive): upgrading cls files and running biblatex fallback."
        )
        _upgrade_outdated_cls_files(tex_dir)
        compat_shims_applied.append({"engine": "*", "stage": 2, "shims": ["upgrade_cls_files"]})

        for engine in engines:
            if original_tex_content is None:
                applied_shims_list = ["skip_shims_source_unreadable"]
            else:
                patched_tex_content, applied_shims_list = _apply_engine_compat_shims(
                    original_tex_content, engine, language
                )
                try:
                    tex_path_obj.write_text(patched_tex_content, encoding="utf-8")
                except Exception as write_err:
                    logger.warning("Stage 2: failed to write shimmed TeX for engine %s: %s", engine, write_err)
                    applied_shims_list = list(applied_shims_list) + ["shim_write_failed"]

            _clean_aux_files()
            compat_shims_applied.append({"engine": engine, "stage": 2, "shims": applied_shims_list})
            logger.info(f"Stage 2 - attempting engine {engine}...")
            result = await _compile_one(engine)
            result = _preserve_pdf_and_log(result, engine, "stage2")
            results[f"stage2_{engine}"] = result
            if _is_perfect(result):
                if language == "cjk" and engine == "pdflatex":
                    logger.debug("Stage 2 pdflatex perfect for CJK; continuing for merit selection")
                else:
                    logger.info(f"Stage 2 (invasive): {engine} produced perfect compilation (DEGRADED).")
                    return _with_diagnostics(
                        {
                            "pdf_path": result.pdf_path,
                            "status": "completed",
                            "engine": engine,
                            "error_count": 0,
                            "warnings": "Stage 2 (invasive) was used: user .cls files may have been modified.",
                            "errors": None,
                        }
                    )

        engine_result_items = [(k.split("_", 1)[1], v) for k, v in results.items()]
        dedup: Dict[str, CompilationResult] = {}
        for eng, res in engine_result_items:
            if eng not in dedup or (dedup[eng].pdf_path is None and res.pdf_path is not None):
                dedup[eng] = res
        result_items_for_selection = list(dedup.items())
        result_items_for_selection_with_pdf = [
            (eng, res)
            for eng, res in result_items_for_selection
            if res.pdf_path is not None and Path(res.pdf_path).exists()
        ]

        for engine, result in dedup.items():
            results[engine] = result
            if result.pdf_path:
                pdf_candidate = Path(result.pdf_path)
                if pdf_candidate.exists():
                    preserved_pdf = Path(normalized_output_dir) / f"{Path(normalized_tex_file).stem}.{engine}.pdf"
                    try:
                        shutil.copy2(pdf_candidate, preserved_pdf)
                        result.pdf_path = str(preserved_pdf)
                        logger.info(f"Preserved {engine} PDF snapshot: {preserved_pdf}")
                        if result.log_path:
                            log_candidate = Path(result.log_path)
                            if log_candidate.exists():
                                preserved_log = Path(normalized_output_dir) / f"{Path(normalized_tex_file).stem}_{engine}.log"
                                try:
                                    shutil.copy2(log_candidate, preserved_log)
                                    logger.info(f"Preserved {engine} LOG snapshot: {preserved_log}")
                                except Exception as exc:
                                    logger.warning(f"Failed to preserve {engine} LOG snapshot: {exc}")
                    except Exception as exc:
                        logger.warning(f"Failed to preserve {engine} PDF snapshot from {pdf_candidate}: {exc}")
                        result.pdf_path = str(pdf_candidate) if pdf_candidate.exists() else None
                else:
                    logger.warning(f"Engine {engine} returned a non-existent PDF path: {pdf_candidate}")
                    result.pdf_path = None

            effective_quality_issue_count = result.quality_issue_count if language == "cjk" else 0
            if result.success and result.error_count == 0 and effective_quality_issue_count == 0:
                if language == "cjk" and engine == "pdflatex":
                    logger.debug("pdflatex produced 0 errors for CJK; continuing for merit selection")
                else:
                    logger.info(f"{engine} produced perfect compilation (zero errors)")
                    return _with_diagnostics(
                        {
                            "pdf_path": result.pdf_path,
                            "status": "completed",
                            "engine": engine,
                            "error_count": 0,
                            "warnings": None,
                            "errors": None,
                        }
                    )

        all_error_lines: List[str] = []
        for res in dedup.values():
            all_error_lines.extend(res.errors)

        _IMAGE_TRIGGERS = ("reading image failed", "pdf inclusion")
        if any(any(kw in ln.lower() for kw in _IMAGE_TRIGGERS) for ln in all_error_lines):
            logger.warning(
                "Stage 3 (image sanitizer): detected PDF inclusion errors - entering iterative repair loop (max %d rounds).",
                MAX_SANITIZE_ROUNDS,
            )
            sanitized_files: set = set()
            all_sanitized_outputs: List[Path] = []

            best_s2_engine = engines[-1]
            if result_items_for_selection_with_pdf:
                best_s2_engine = min(result_items_for_selection_with_pdf, key=lambda x: x[1].error_count)[0]
            elif result_items_for_selection:
                best_s2_engine = min(result_items_for_selection, key=lambda x: x[1].error_count)[0]

            round_error_lines = all_error_lines
            current_round_result: Optional[CompilationResult] = None
            for round_idx in range(MAX_SANITIZE_ROUNDS):
                has_image_error = any(any(kw in ln.lower() for kw in _IMAGE_TRIGGERS) for ln in round_error_lines)
                if not has_image_error:
                    logger.info("Stage 3 round %d: no image errors detected; exiting loop.", round_idx)
                    break

                newly_sanitized_outputs, any_new, newly_sanitized_originals = try_sanitize_images_in_errors(
                    round_error_lines,
                    Path(tex_dir),
                    already_sanitized=sanitized_files,
                )
                if not any_new:
                    logger.info("Stage 3 round %d: no new corrupted PDFs discovered (short-circuit).", round_idx)
                    break

                sanitized_files.update(newly_sanitized_originals)
                all_sanitized_outputs.extend(newly_sanitized_outputs)
                logger.info(
                    "Stage 3 round %d: repaired %d new PDF(s) - cumulative total %d.",
                    round_idx,
                    len(newly_sanitized_originals),
                    len(sanitized_files),
                )

                _clean_aux_files()
                logger.info("Stage 3 round %d - retrying engine %s after image sanitization...", round_idx, best_s2_engine)
                current_round_result = await _compile_one(best_s2_engine)
                current_round_result = _preserve_pdf_and_log(current_round_result, best_s2_engine, f"stage3_r{round_idx}")
                results[f"stage3_r{round_idx}_{best_s2_engine}"] = current_round_result

                if _is_perfect(current_round_result):
                    logger.info("Stage 3 round %d: %s produced perfect compilation.", round_idx, best_s2_engine)
                    return _with_diagnostics(
                        {
                            "pdf_path": current_round_result.pdf_path,
                            "status": "completed_with_warnings",
                            "engine": best_s2_engine,
                            "error_count": 0,
                            "warnings": (
                                f"Stage 3 (image sanitizer) repaired {len(all_sanitized_outputs)} corrupted PDF image(s) "
                                f"across {round_idx + 1} round(s): " + ", ".join(p.name for p in all_sanitized_outputs)
                            ),
                            "errors": None,
                        }
                    )

                if current_round_result.pdf_path and current_round_result.error_count < sum(res.error_count for res in dedup.values()):
                    logger.info("Stage 3 round %d: %s reduced errors; accepting best-effort PDF.", round_idx, best_s2_engine)
                    return _with_diagnostics(
                        {
                            "pdf_path": current_round_result.pdf_path,
                            "status": "completed_with_warnings",
                            "engine": best_s2_engine,
                            "error_count": current_round_result.error_count,
                            "warnings": (
                                f"Stage 3 (image sanitizer) partially repaired {len(all_sanitized_outputs)} image(s) "
                                f"across {round_idx + 1} round(s). {current_round_result.error_count} residual error(s)."
                            ),
                            "errors": None,
                        }
                    )

                round_error_lines = current_round_result.errors

        engines_with_pdf = result_items_for_selection_with_pdf
        if language == "cjk":
            modern_engines_with_pdf = [(e, r) for e, r in engines_with_pdf if e in ["xelatex", "lualatex"]]
            if modern_engines_with_pdf:
                logger.info("Found modern-engine PDFs for CJK; excluding pdflatex result.")
                engines_with_pdf = modern_engines_with_pdf

        if engines_with_pdf:
            engines_with_pdf.sort(
                key=lambda x: (
                    x[1].error_count,
                    x[1].quality_issue_count if language == "cjk" else 0,
                )
            )
            best_engine, best_result = engines_with_pdf[0]
            if language == "cjk":
                comparison = ", ".join(f"{eng}: errors={res.error_count}, quality={res.quality_issue_count}" for eng, res in dedup.items())
            else:
                comparison = ", ".join(f"{eng}: {res.error_count}" for eng, res in dedup.items())
            logger.warning(f"Selected {best_engine} PDF with {best_result.error_count} errors ({comparison})")
            warning_msg = f"Compilation completed with {best_result.error_count} errors using {best_engine}."
            if language == "cjk" and best_result.quality_issue_count > 0:
                warning_msg += (
                    f" Detected {best_result.quality_issue_count} CJK missing-character quality issues in the chosen engine log."
                )
            return _with_diagnostics(
                {
                    "pdf_path": best_result.pdf_path,
                    "status": "completed_with_warnings",
                    "engine": best_engine,
                    "error_count": best_result.error_count,
                    "warnings": warning_msg,
                    "errors": None,
                }
            )

        logger.error(f"All stages and engines failed to produce PDF: {engines}")
        combined_errors = "Compilation failed with all engines across all stages:\n\n"
        for eng, res in dedup.items():
            combined_errors += f"{eng} ({res.error_count} errors):\n"
            combined_errors += "\n".join(res.errors[:10]) + "\n\n"
        total_errors = sum(res.error_count for res in dedup.values())
        return _with_diagnostics(
            {
                "pdf_path": None,
                "status": "failed_compilation",
                "engine": None,
                "error_count": total_errors,
                "warnings": None,
                "errors": combined_errors,
            }
        )
    except asyncio.CancelledError:
        logger.info("compile_with_intelligent_fallback_async cancelled")
        raise
    finally:
        if original_tex_content is not None:
            try:
                tex_path_obj.write_text(original_tex_content, encoding="utf-8")
            except Exception as restore_err:
                logger.warning("Failed to restore original TeX source after async fallback compile: %s", restore_err)


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
                logger.info(f"Compilation succeeded: {result['pdf_path']}")
                return result["pdf_path"]
            else:
                logger.error(f"Compilation failed: {result.get('errors', 'Unknown error')}")
                raise Exception(result.get("errors", "Compilation failed"))
        
        except Exception as e:
            logger.error(f"Compilation error: {e}")
            raise

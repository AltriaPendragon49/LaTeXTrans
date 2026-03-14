"""
PDF Sanitizer Module — Environmental Fallback (Image Sanitizer)
================================================================

Provides non-destructive detection and repair of byte-level corrupted PDF
image files.  This is designed exclusively for the "translate published
papers" use-case: source PDFs are historical artefacts that cannot be
changed upstream, so automatic repair is both safe and user-friendly.

Design invariants
-----------------
* The **original file is never overwritten**.
* The sanitized file is written to ``<original_stem>.sanitized.pdf`` in the
  same directory.
* All repair actions are logged explicitly. Nothing is silent.
* If Ghostscript is not installed the sanitizer degrades gracefully (no-op).

Trigger conditions (caller is responsible for deciding when to call)
---------------------------------------------------------------------
* LaTeX compilation error lines contain: ``pdf inclusion: reading image failed``
* AND ``pdfinfo`` reports a Syntax Error on the same file.
"""

import re
import shutil
import subprocess
import sys
import logging
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# Packages known to crash or degrade modern CJK engines (XeLaTeX/LuaLaTeX).
# These are typically accessibility or PDF-metadata packages relying on
# pdfTeX-only primitives.
_CONFLICT_PACKAGES = {
    "axessibility": "Incompatible with XeLaTeX/LuaLaTeX (uses pdfTeX primitives)",
    "accsupp": "Known to cause CJK character mapping issues",
    "pdfcomment": "Relies on pdfTeX-only specials",
}


def apply_precompile_sanitization(tex_content: str) -> Tuple[str, List[str]]:
    """
    Stage 0 Sanitization: Remove/Comment out incompatible packages before compilation.

    Scans for \\usepackage{...} and matches against _CONFLICT_PACKAGES.
    Returns (sanitized_content, list_of_warnings).
    """
    warnings = []
    sanitized_lines = []

    # Regex to capture \usepackage[options]{package1,package2...}
    # Group 1: optional arguments [..]
    # Group 2: package list
    pkg_pattern = re.compile(r"\\usepackage\s*(?:\[[^\]]*\])?\s*\{([^}]*)\}")

    for line in tex_content.splitlines():
        trimmed = line.strip()
        if not trimmed.startswith("\\usepackage"):
            sanitized_lines.append(line)
            continue

        match = pkg_pattern.search(line)
        if not match:
            sanitized_lines.append(line)
            continue

        packages = [p.strip() for p in match.group(1).split(",")]
        conflicts = [p for p in packages if p in _CONFLICT_PACKAGES]

        if conflicts:
            # Comment out the entire line and add a reason
            reasons = "; ".join(set(_CONFLICT_PACKAGES[p] for p in conflicts))
            sanitized_line = f"% {line} % Sanitized: {reasons}"
            sanitized_lines.append(sanitized_line)
            msg = f"Stage 0 (pre-compile): commented out incompatible package(s) {conflicts}. Reason: {reasons}"
            warnings.append(msg)
            logger.info(msg)
        else:
            sanitized_lines.append(line)

    return "\n".join(sanitized_lines), warnings


def _find_ghostscript() -> Optional[str]:
    """Return the Ghostscript executable name available on this system.

    On Windows the binary is typically ``gswin64c`` or ``gswin32c``;
    on Linux/macOS it is simply ``gs``.
    Returns *None* if no Ghostscript installation is found.
    """
    candidates = ["gswin64c", "gswin32c", "gs"] if sys.platform == "win32" else ["gs"]
    for name in candidates:
        loc = shutil.which(name)
        if loc:
            return loc

    # Windows specific: fallback to common installation directories if not in PATH
    if sys.platform == "win32":
        # Check D:\apps, C:\Program Files, C:\Program Files (x86)
        roots = [Path("D:/apps"), Path("C:/Program Files"), Path("C:/Program Files (x86)")]
        for root in roots:
            if not root.exists():
                continue
            gs_root = root / "gs"
            if gs_root.exists() and gs_root.is_dir():
                # Find the latest version folder like gs10.06.0
                versions = sorted(list(gs_root.glob("gs*")), reverse=True)
                for v in versions:
                    bin_dir = v / "bin"
                    if bin_dir.exists():
                        for name in ["gswin64c.exe", "gswin32c.exe"]:
                            gs_path = bin_dir / name
                            if gs_path.exists():
                                logger.info(f"Ghostscript found via path-fallback: {gs_path}")
                                return str(gs_path)
    return None

# ---------------------------------------------------------------------------
# Pattern to extract "(file …)" from a LaTeX log error line
# Example: ./sec/5_experiments.tex:58: error:  (file imgs/HOTA.pdf)
# ---------------------------------------------------------------------------
_PDF_INCLUSION_RE = re.compile(
    r'\(file\s+([^)]+\.pdf)\)',
    re.IGNORECASE,
)

# LaTeX \includegraphics path pattern for a specific PDF stem
_INCLUDEGRAPHICS_RE = re.compile(
    r'(\\includegraphics(?:\[[^\]]*\])?\{)([^}]*?)(\})',
)


def extract_failed_pdf_paths(error_lines: List[str], tex_dir: Path) -> List[Path]:
    """
    Parse compiled LaTeX error lines and return absolute paths of PDF files
    that triggered a PDF inclusion failure.

    Matches on either ``reading image failed`` or ``pdf inclusion`` as trigger
    phrases.  This handles cases where LaTeX splits the error text across log
    lines (the continuation-merge in ``parse_log_errors`` should join them, but
    we stay resilient to partial matches too).

    Only returns paths that actually exist on disk.
    """
    _TRIGGER_PHRASES = ["reading image failed", "pdf inclusion"]
    failed: List[Path] = []

    for line in error_lines:
        line_lower = line.lower()
        if not any(phrase in line_lower for phrase in _TRIGGER_PHRASES):
            continue
        match = _PDF_INCLUSION_RE.search(line)
        if match:
            rel = match.group(1).strip()
            candidate = (tex_dir / rel).resolve()
            if candidate.exists() and candidate not in failed:
                failed.append(candidate)

    return failed


def check_pdf_syntax_error(pdf_path: Path) -> bool:
    """
    Use ``pdfinfo`` to check whether a PDF has byte-level syntax errors.

    Returns True if a Syntax Error or Illegal character is detected.
    Returns False if the file is fine.

    Raises:
        RuntimeError: when pdfinfo is unavailable or cannot execute.
    """
    try:
        result = subprocess.run(
            ["pdfinfo", str(pdf_path)],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        combined = result.stdout + result.stderr
        return "Syntax Error" in combined or "Illegal character" in combined
    except FileNotFoundError:
        raise RuntimeError("pdfinfo is required but not installed")
    except Exception as exc:
        raise RuntimeError(f"pdfinfo check failed for {pdf_path.name}: {exc}") from exc


def sanitize_pdf(pdf_path: Path) -> Optional[Path]:
    """
    Use Ghostscript to distil a corrupted PDF into a clean structural clone.

    The original file is **never modified**.  The sanitized clone is written
    to ``<stem>.sanitized.pdf`` in the same directory.

    Returns the path to the sanitized PDF on success, or None on failure.
    """
    sanitized_path = pdf_path.with_name(pdf_path.stem + ".sanitized.pdf")

    # Warn if output already exists (idempotent: we overwrite it)
    existed = sanitized_path.exists()

    gs_bin = _find_ghostscript()
    if gs_bin is None:
        logger.warning(
            "Ghostscript not found (tried gs/gswin64c/gswin32c); "
            "cannot sanitize %s.  Install Ghostscript to enable "
            "automatic PDF repair.",
            pdf_path.name,
        )
        return None

    try:
        proc = subprocess.run(
            [
                gs_bin,
                "-sDEVICE=pdfwrite",
                "-dCompatibilityLevel=1.4",
                "-dNOPAUSE",
                "-dBATCH",
                "-dQUIET",
                f"-sOutputFile={sanitized_path}",
                str(pdf_path),
            ],
            capture_output=True,
            check=True,
            timeout=60,
        )
        if sanitized_path.exists() and sanitized_path.stat().st_size > 0:
            action = "Overwrote" if existed else "Created"
            logger.warning(
                "⚠️  IMAGE SANITIZER: Detected graphic file '%s' is structurally "
                "corrupted at the byte level.  %s sanitized instance '%s' for "
                "compilation.  Original file preserved.  (using %s)",
                pdf_path.name,
                action,
                sanitized_path.name,
                gs_bin,
            )
            print(
                f"\n⚠️  IMAGE SANITIZER\n"
                f"   Source PDF:    {pdf_path}\n"
                f"   Status:        byte-level syntax error detected\n"
                f"   Sanitized to:  {sanitized_path}\n"
                f"   Original file: preserved (not modified)\n"
            )
            return sanitized_path
        else:
            logger.error("Ghostscript produced empty/missing output for %s", pdf_path.name)
            return None

    except FileNotFoundError:
        logger.warning(
            "Ghostscript (%s) not found; cannot sanitize %s.  "
            "Install Ghostscript to enable automatic PDF repair.",
            gs_bin, pdf_path.name,
        )
        return None
    except subprocess.CalledProcessError as exc:
        logger.error("Ghostscript failed for %s: %s", pdf_path.name, exc)
        if sanitized_path.exists():
            sanitized_path.unlink(missing_ok=True)
        return None
    except subprocess.TimeoutExpired:
        logger.error("Ghostscript timed out for %s", pdf_path.name)
        sanitized_path.unlink(missing_ok=True)
        return None
    except Exception as exc:
        logger.error("Unexpected sanitizer error for %s: %s", pdf_path.name, exc)
        return None


def patch_tex_includegraphics(tex_content: str, original: Path, sanitized: Path) -> Tuple[str, int]:
    """
    Replace ``\\includegraphics{...original.pdf...}`` with the sanitized
    filename in the TeX source string.

    Returns (patched_content, replacement_count).
    """
    orig_stem = original.stem          # e.g. "HOTA"
    san_name  = sanitized.name         # e.g. "HOTA.sanitized.pdf"
    orig_name = original.name          # e.g. "HOTA.pdf"
    count = 0

    def _replace(m: re.Match) -> str:
        nonlocal count
        prefix, inner, suffix = m.group(1), m.group(2), m.group(3)
        # Match if inner path ends with original filename (with or without directory prefix)
        inner_stripped = inner.replace("\\", "/")
        if inner_stripped.endswith("/" + orig_name) or inner_stripped == orig_name:
            # Replace just the filename component, keep directory prefix intact
            dir_part = inner_stripped[: -(len(orig_name))]
            count += 1
            return prefix + dir_part.replace("/", "/") + san_name + suffix
        return m.group(0)

    patched = _INCLUDEGRAPHICS_RE.sub(_replace, tex_content)
    return patched, count


def try_sanitize_images_in_errors(
    error_lines: List[str],
    tex_dir: Path,
    already_sanitized: Optional[set] = None,
) -> Tuple[List[Path], bool, set]:
    """Sanitize corrupted PDFs and recursively patch ALL .tex files.

    Args:
        error_lines: Lines from the LaTeX compilation log to scan for image errors.
        tex_dir: Root directory of the LaTeX project.
        already_sanitized: Set of PDF paths that have already been repaired in
            previous rounds of the iterative loop.  Files present in this set
            will be skipped — each PDF is distilled at most once.

    Returns:
        (newly_sanitized_list, any_newly_sanitized, newly_sanitized_set)
        *newly_sanitized_list*  — sanitized output paths produced this round.
        *any_newly_sanitized*   — True if at least one new PDF was repaired.
        *newly_sanitized_set*   — Set of original PDF paths repaired this round
                                  (to be merged into the caller's accumulator).
    """
    if already_sanitized is None:
        already_sanitized = set()

    failed_pdfs = extract_failed_pdf_paths(error_lines, tex_dir)
    if not failed_pdfs:
        return [], False, set()

    # Only process PDFs that have NOT been sanitized in a previous round.
    new_failed_pdfs = [p for p in failed_pdfs if p not in already_sanitized]
    if not new_failed_pdfs:
        logger.info(
            "Stage 3: all %d detected corrupted PDF(s) were already sanitized in previous rounds; "
            "short-circuiting.",
            len(failed_pdfs),
        )
        return [], False, set()

    sanitized_list: List[Path] = []
    newly_sanitized_originals: set = set()

    # Identify which new PDFs need patching
    pdf_to_sanitized = {}
    for pdf_path in new_failed_pdfs:
        if not check_pdf_syntax_error(pdf_path):
            logger.info(
                "PDF %s triggered reading failure but pdfinfo reports no syntax error; skipping sanitizer.",
                pdf_path.name,
            )
            continue

        san = sanitize_pdf(pdf_path)
        if san:
            pdf_to_sanitized[pdf_path] = san
            sanitized_list.append(san)
            newly_sanitized_originals.add(pdf_path)

    if not sanitized_list:
        return [], False, set()

    # Recursively find and patch ALL .tex files in the project
    tex_files = list(tex_dir.rglob("*.tex"))
    logger.info("Stage 3: scanning %d .tex file(s) for image reference patching...", len(tex_files))

    for tex_file in tex_files:
        try:
            content = tex_file.read_text(encoding="utf-8", errors="replace")
            original_content = content
            total_patches = 0

            for pdf_path, san_path in pdf_to_sanitized.items():
                content, count = patch_tex_includegraphics(content, pdf_path, san_path)
                total_patches += count

            if total_patches > 0 and content != original_content:
                tex_file.write_text(content, encoding="utf-8")
                logger.info("Stage 3: patched %d reference(s) in %s", total_patches, tex_file.relative_to(tex_dir))
        except Exception as e:
            logger.warning("Stage 3: failed to patch %s: %s", tex_file, e)

    return sanitized_list, len(sanitized_list) > 0, newly_sanitized_originals

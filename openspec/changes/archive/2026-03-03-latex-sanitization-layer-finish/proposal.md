# Proposal: Multi-Stage LaTeX Sanitization Layer

## Goal
To establish a comprehensive sanitization layer that prevents and repairs compilation failures caused by environmental or semantic conflicts. This includes:
- **Iterative Image Repair**: Sequentially detecting and distilling corrupted PDFs across multiple compilation rounds.
- **Pre-Compile Filtering**: Automatically removing incompatible packages (e.g., `axessibility`) that crash modern LaTeX engines in CJK mode.

## Context
1.  **Stage 3 (Post-Failure Repair)**: Handles byte-level corrupted PDFs by using Ghostscript to distill them and patching the TeX source.
2.  **Stage 0 (Pre-Compile Prevention)**: Filters the TeX source before compilation to comment out packages known to conflict with XeLaTeX/LuaLaTeX in CJK environments (e.g., `axessibility`).

## Proposed Changes

### 1. LaTeX Compiler (`compiler.py`)
- **Error Parsing**: Enhanced `parse_log_errors` regex and multi-line merging to reliably detect image failures.
- **Retry Logic**: Trigger Stage 3 (Image Sanitizer) immediately upon detecting image errors, even if a degraded PDF exists.
- **Pre-hook**: Inject `apply_precompile_sanitization` (Stage 0) before the first compilation attempt.

### 2. Sanitizer Service (`sanitizer.py`)
- **Image Sanitizer (Iterative)**:
    - **Loop Model**: Iteratively detect bad PDFs, distill with Ghostscript, and patch TeX until success or max rounds (20).
    - **Path-fallback**: Reliable Ghostscript detection on Windows.
    - **Recursive Patching**: Updates `\includegraphics` in all project sub-files.
- **Pre-Compile Sanitizer**:
    - **Regex Detection**: Identify conflicting packages like `axessibility` or `accsupp`.
    - **Notice Injection**: Comment out triggering lines with explanatory `% Sanitized` headers.

## Impact
- **Reliability**: Significantly reduces "Exit Code 1" failures due to legacy artifacts or engine-specific primitives.
- **Traceability**: All sanitization actions are recorded in `task_log.json`.

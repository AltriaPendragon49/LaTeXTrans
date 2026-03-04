# Design: LaTeX Sanitization Layer

## Architecture

The sanitization layer operates in two interleaved stages around the main LaTeX compilation loop:

### Stage 0: Pre-Compile Sanitization (Preventive)
- **Timing**: After translation assembly, before any `subprocess.run(xelatex/lualatex)`.
- **Logic**: 
    - scans `.tex` content for `\usepackage{...}`.
    - Matches against a `CONFLICT_RULES` matrix (e.g., `PDFTEX_ONLY_PRIMITIVES`).
    - Comments out triggering lines: `%\usepackage{axessibility} % Sanitized: Incompatible with XeLaTeX`.
- **Reasoning**: Many papers use accessibility or PDF-commenting packages that rely on pdfTeX-only primitives which crash modern CJK engines.

### Stage 3: Iterative Image Sanitizer (Reactive)
- **Timing**: Triggered only if Stage 1/2 fails with "pdf inclusion: reading image failed".
- **Logic**:
    - **Goal-Driven Loop**: Iteratively find and fix bad PDFs until compilation succeeds or `MAX_SANITIZE_ROUNDS=20` is hit.
    - **Discovery**: Extract failed PDF path from log lines → Confirm via `pdfinfo` → Distill via Ghostscript.
    - **Recursive Patching**: Sub-files are checked and updated to ensure consistency.
- **Invariants**:
    - **🔒 Compilation-Driven**: No proactive scanning; only triggered by evidence in logs.
    - **🔒 Non-Destructive**: Original PDFs preserved; sanitized as `<stem>.sanitized.pdf`.
    - **🔒 Monotonic Convergence**: `sanitized_files` set only grows; each PDF distilled at most once; loop exits if no new discoveries.
- **GS Detection**: Uses a robust fallback search on Windows.

## Traceability
Each action must emit a structured log event:
```json
{
  "stage": "sanitization",
  "type": "pre_compile / image_repair",
  "target": "package_name / file_path",
  "action": "comment / distill",
  "reason": "..."
}
```

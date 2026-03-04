# Design: Restore Structural Integrity

## 1. Hard Freeze Mechanism (Input Layer Defense)
Instead of relying on LLM self-restraint and post-fix validation, we will perform a physical string replacement during parsing.
- **Target:** `$...$`, `\(...\)`, `\[...\]`, `\begin{equation/align/figure/table/...}`, `\label{...}`, `\ref{...}`, `\cite{...}`.
- **Implementation:** 
  - Use regex or pylatexenc to identify blocks.
  - Replace them with a typed token: `[PH_MATH_001]`, `[PH_FIG_002]`, `[PH_CMD_003]`.
  - Keep a mapping `Dict[str, str]` of `token -> original_latex`.
- **Validation:** After LLM translation, count all `[PH_*]` inside the text. If they do not identically match the input tokens, the translation for that chunk fails.

## 2. Structure-Aware Chunking
The current `_chunk_long_sections` heavily relies on `tiktoken` limits causing splits inside `{}` and `\begin/end` blocks.
- **New Logic:** 
  1. Parse the section into block-level elements (paragraphs).
  2. Sub-chunking only at safe punctuation marks (`。`, `.`) where LaTeX brace depth equals 0 and currently not inside any environment/math block.
  3. If a block is too large and cannot be safely chunked, we return a `Warning` and skip translation, defaulting to source copy, preventing structural corruption.

## 3. Limit Pre-Compile Fixes
The `_escape_bare_underscores_in_text_mode` causes false positives (corrupts math).
- **Update:** Only apply this if we are 100% sure the string is outside math limits. With the proposed *Hard Freeze*, all math mode is hidden (`[PH_MATH_...]`). Therefore, any `_` left in the text is genuinely textual and safe to escape.

## 4. Fail-Fast vs Structural Fallback
- Eradicate the `structural_fallback` regex stitching routine in `translator_agent.py`.
- If a chunk exceeds retry limits due to a validation error, mark the section translation as `FAILED`.
- Provide precise diagnostics: `Error: Chunk 5 mismatch on [PH_MATH_002]`.

## 5. Tiered Compilation Strategy
Refactor `compiler.py` flow:
- **Stage 0 (Pristine):** Run `latexmk` without touching any `.cls` or `.bbl` files and without shim injections.
- **Stage 1 (Minimal Shims):** If Stage 0 fails, inject compatible shims (e.g., `\pdfglyphtounicode`) but do NOT delete user files.
- **Stage 2 (Invasive Strategy):** If Stage 1 fails, attempt aggressive fallbacks like deleting bundled `.cls` or stripping `biblatex`. Warn the user that compilation is degraded.

## 6. Environmental Fallback (Image Sanitizer)
To prevent strictly compliant LaTeX engines (LuaLaTeX/XeLaTeX) from crashing due to byte-level corruption in published PDFs, we introduce a non-destructive image sanitizer.
- **Trigger Condition:** Compilation fails with `pdf inclusion: reading image failed` or equivalent, AND `pdfinfo` or `pdftotext` reports a syntax error on the source PDF.
- **Mechanism:** Automatically distil the corrupted PDF using Ghostscript (`gs -sDEVICE=pdfwrite`) to create a structurally sound clone.
- **Safety Guarantee:** The original file is NEVER overwritten. The sanitized file is yielded as `<image_name>.sanitized.pdf`, and the `.tex` file `\includegraphics` command is updated to point to the sanitized version.
- **User Transparency:** Must explicitly log warning: "Detected graphic file `<file>.pdf` is structurally corrupted. Automatically generated a sanitized instance `<file>.sanitized.pdf` for compilation. Original file preserved."

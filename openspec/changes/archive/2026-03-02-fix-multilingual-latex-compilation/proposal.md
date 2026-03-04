# Multilingual LaTeX Architecture Reboot

## Problem
The current system operates on a flawed dynamic-fallback and log-scraping strategy that attempts to fix font and compiler issues on the fly. This architecture breaks fundamental LaTeX principles:
1. **Fonts are System Resources**: `\setCJKmainfont` fails cleanly on `xelatex` if the font isn't installed natively on the host OS. Passing random font strings in the preamble attempts to treat system resources as document traits.
2. **Missing Fonts Cause Semantic Destruction without Errors**: When `xelatex` fails, the compiler falls back to `lualatex`/`pdflatex`. However, these engines don't support `xeCJK`. They ignore the package, leave font commands undefined, and print configuration syntax (like `[FallbackFonts=...]`) as plain text. The actual CJK characters vanish completely (missing font glyphs), yielding a "successful" PDF that is entirely blank of translated text.
3. **Latin Languages are Sabotaged**: To appease the `xelatex` fallback, the current codebase actively strips native `pdflatex` packages like `[T1]{fontenc}` from Latin-script translations (French, Spanish, German). This destroys native hyphenation and encoding just to prevent a secondary engine from throwing an error.

## Solution

We enforce a strict, abstracted architecture: **Language determines the package. Fonts are a system capability. Engines are dumb executors.**

1. **Zero-Touch for Latin/English Scripts**:
   - `en`, `de`, `fr`, `es`, `it`, etc., undergo **no preamble manipulation**. We stop stripping `[T1]{fontenc}` or `newtxtext`. The document is passed directly to the engines. `pdflatex` will natively handle the semantics flawlessly.
2. **Unified Static Mapping for CJK**:
   - **Chinese (`zh`)**: `\usepackage[UTF8]{ctex}`
   - **Japanese (`ja`)**: `\usepackage{luatexja}` (Strict LuaLaTeX enforcement. Prevents `xeCJK` leakage).
   - **Korean (`ko`)**: `\usepackage{kotex}` (Multi-engine safe).
3. **Fonts Reside in the OS**:
   - All dynamic `\setCJKmainfont` or `[FallbackFonts=]` logic is **deleted** entirely. The system assumes Noto CJK is installed on the underlying OS (Windows/Linux Docker) and relies on the macro packages to invoke them naturally.
4. **Fail-Fast Engine Roulette**:
   - The multi-engine queue (`pdflatex -> xelatex -> lualatex`) remains. However, because we statically inject `luatexja` for Japanese, `pdflatex` and `xelatex` will explicitly crash when attempting to process it. This fail-fast mechanism guarantees the queue skips to `lualatex`, producing a semantically perfect PDF.

## Rationale
- Completely eliminates "silent character loss" (semantic corruption), as language packages are hard-bound and won't be bypassed.
- Restores perfect typography for Latin languages.
- Massively simplifies `utils.py` by removing engine-specific parsing, font subsetting, and fallback guesswork.
- Scalable design logic: new languages follow a 1-to-1 package mapping system without needing recursive engine/font debugging.

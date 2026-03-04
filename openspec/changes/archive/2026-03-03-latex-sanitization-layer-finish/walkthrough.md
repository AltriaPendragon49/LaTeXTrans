# Walkthrough: LaTeX Sanitization Layer

Established a dual-defense sanitization layer to handle common CJK LaTeX compilation failure modes.

## Phase 1: Pre-Compile Sanitization (Stage 0)
Prevents modern engines (XeLaTeX/LuaLaTeX) from crashing on incompatible legacy packages.

- **Trigger**: Automatic when `language == "cjk"` is detected during compilation.
- **Action**: Scans all `.tex` files; comments out `axessibility`, `accsupp`, and `pdfcomment`.
- **Traceability**: Warnings are injected into the final compilation result and logs.

## Phase 2: Iterative Image Sanitizer (Stage 3)
Sequentially repairs multiple byte-level corrupted PDFs discovered during compilation.

- **Loop Model**: If compilation fails due to PDF inclusion, the sanitizer:
  1. Extracts the bad PDF path from logs.
  2. Verifies corruption with `pdfinfo`.
  3. Distills with `Ghostscript`.
  4. Patches all `\includegraphics` references in the project.
  5. Retries compilation using the best engine from Stage 2.
- **Safety**:
  - `MAX_SANITIZE_ROUNDS = 20` hard cap.
  - Monotonic convergence (only newly discovered bad PDFs are repaired).
  - Short-circuits immediately on success or if no new bad PDFs are found.

## Verification Results
- **Unit Tests**: 20/20 passed (`backend/tests/unit/test_precompile_sanitizer.py` and `test_sanitizer.py`).
- **Regression Test**: Verified successful iterative repair on the `a211bdb6` failure case (sequential repair of `HOTA.pdf` and `SOTA_v2.pdf`).

## Artifacts Created/Modified
- [sanitizer.py](file:///d:/future/antigravity/LaTexTrans/backend/app/services/latex/sanitizer.py): Core logic for GS detection, iterative repair, and package filtering.
- [compiler.py](file:///d:/future/antigravity/LaTexTrans/backend/app/services/latex/compiler.py): Integrated Stage 0 and Stage 3 loops.
- [test_precompile_sanitizer.py](file:///d:/future/antigravity/LaTexTrans/backend/tests/unit/test_precompile_sanitizer.py): New tests for package filtering.

# Tasks for Multilingual LaTeX Compilation Architecture

- [x] **Refactor `utils.py` abstraction layer**:
    - [x] Find the `add_cjk_package` function.
    - [x] Strip out all hardcoded font definitions (e.g., `IPAexMincho`, `UnBatang`, `Noto Serif CJK JP`).
    - [x] Implement strict 1-to-1 language-to-package mappings:
        - [x] `ja` -> `\usepackage{luatexja}`
        - [x] `ko` -> `\usepackage{kotex}`
        - [x] `zh` -> `\usepackage[UTF8]{ctex}`
    - [x] **CRITICAL**: Remove the call to `_comment_out_pdflatex_commands` for Latin-script languages (`en`, `de`, `fr`, `es`, `it`, `nl`, `pl`). Implement a pure pass-through (Zero-Touch) for them.
- [x] **Verify Simplification and Regression**:
    - [x] Compile Korean and Japanese using the new simplified strings to ensure the correct engine inherently succeeds within the fallback loop.
    - [x] Compile a French or German text to verify the `[T1]{fontenc}` package remains intact and compiles beautifully on `pdflatex`.
    - [x] Run unit tests to ensure `utils.py` passes all logic requirements.

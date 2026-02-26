# Tasks for Multilingual LaTeX Compilation Architecture

1.  **Refactor `utils.py` abstraction layer**:
    *   Find the `add_cjk_package` function.
    *   Strip out all hardcoded font definitions (e.g., `IPAexMincho`, `UnBatang`, `Noto Serif CJK JP`).
    *   Implement strict 1-to-1 language-to-package mappings:
        *   `ja` -> `\usepackage{luatexja}`
        *   `ko` -> `\usepackage{kotex}`
        *   `zh` -> `\usepackage[UTF8]{ctex}`
    *   **CRITICAL**: Remove the call to `_comment_out_pdflatex_commands` for Latin-script languages (`en`, `de`, `fr`, `es`, `it`, `nl`, `pl`). Implement a pure pass-through (Zero-Touch) for them.
2.  **Verify Simplification and Regression**:
    *   Compile Korean and Japanese using the new simplified strings to ensure the correct engine inherently succeeds within the fallback loop.
    *   Compile a French or German text to verify the `[T1]{fontenc}` package remains intact and compiles beautifully on `pdflatex`.
    *   Run unit tests to ensure `utils.py` passes all logic requirements.

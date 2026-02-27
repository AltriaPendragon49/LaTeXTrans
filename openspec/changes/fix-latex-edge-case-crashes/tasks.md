# Tasks: fix-latex-edge-case-crashes

## 1. LuaTeX Compatibility and Early Page Fixes
- [x] 1.1 Globally strip `\pdfoutput=1` in `utils.py/add_cjk_package` to prevent `=1` literal evaluation on LuaLaTeX early pages.
- [x] 1.2 Wipe engine-specific auxiliary files (`.out`, `.aux`, `.toc`, `.fls`, `.fdb_latexmk`, `.xdv`, `.nav`, `.snm`) between compilation attempts in `compiler.py` to prevent cross-engine contamination (like `0<</S/D>>`).

## 2. Robust CJK Environment
- [x] 2.1 Add `_inject_cjk_dummy_environments(latex_code)` to `utils.py` that safely handles undefined `CJK` environments without clashing with `xeCJK`.
- [x] 2.2 Call `_inject_cjk_dummy_environments` in `utils.py/add_cjk_package` during Chinese target processing.
- [x] 2.3 Verify `zh_2508.18791` compiles safely, passing over the dummy block without fatal `Environment CJK undefined` crashes.

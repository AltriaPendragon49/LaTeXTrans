# Tasks for Fix Translation Config Persistence

## 1. Backend Language Setup
- [x] Create language dictionary in `prompts.py` mapping shorthand codes (`ja`, `ko`, `es`...) to full words like `"Japanese"`.
- [x] Extend LaTeX generation with `add_cjk_package()` to dynamically inject `.sty` packages inside `utils.py`.
- [x] Allow `LatexConstructor` to parse the `target_language` parameter, injecting dynamic packages.
- [x] Extract target_language in `generator_agent.py` and forward it downstream.

## 2. In-Memory Configuration Updates 
- [x] Allow passing `source_language` and `target_language` as arguments inside `update_task` method in `task_manager.py`.
- [x] Sync update to database with `db_updates`.

## 3. Database Persistence Fixes
- [x] Wait until translation begins before performing Supabase data commit inside `/translate/{task_id}` (`start_translation`).
- [x] Set accurate in-memory values containing language details via `update_task` *prior* to db persist in both single upload and arXiv batch.
- [x] Verify API payload properly fetches all `advanced_config` settings off to `history.py` backend.
- [x] Confirm translation history correctly renders exact `source_language` mapped backwards.

## 4. Font Rendering & LaTeX Compilation Fixes (NEW)
- [x] Identify and fix Cyrillic font rendering issue by injecting `fontspec` and `CMU Serif` font, and commenting out incompatible pdflatex-specific packages.
- [x] Fix Korean and Japanese font support by configuring `xeCJK` with specific fonts (`UnBatang`/`IPAexMincho`) regardless of whether the `xeCJK` package already exists in the document.
- [x] Setup Latin extended language (`de`, `fr`, `es`) compatibility for `xelatex` fallback by commenting out pdflatex primitives while preserving native pdflatex font configuration.
- [x] Extend `detect_document_language` in `compiler.py` to correctly identify Cyrillic script documents and prioritize the `xelatex` engine, eliminating wasted pdflatex compilation attempts.

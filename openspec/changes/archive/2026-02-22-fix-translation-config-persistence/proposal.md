# Change: Fix Translation Config Persistence

## Why
Currently, when a user translates a paper (either single or batch), the system saves the default language configuration (`zh` and `en`) instead of the actual user-selected languages. This also applies to other advanced configuration options during the initial task creation phase. As a result, the translation history page always displays the default configurations instead of the real configurations used for the translation task. Additionally, the backend LaTeX compilation engine lacked dynamic injection of appropriate CJK packages for non-Chinese languages.

## What Changes
- Implement dynamic CJK package injection in the LaTeX constructor based on the target language.
- Refine LaTeX font and package injection for all supported languages (`zh`, `ja`, `ko`, `ru`, `de`, `fr`, `es`, `en`), ensuring proper fonts are configured (e.g., `UnBatang` for Korean, `IPAexMincho` for Japanese) and Cyrillic uses `fontspec` with `CMU Serif`.
- Optimize language detection in `compiler.py` to identify Cyrillic documents and prioritize the `xelatex` compiler, avoiding wasted `pdflatex` compilation attempts.
- Ensure pdfLaTeX primitive commands are safely commented out for Latin extended languages (`de`, `fr`, `es`) to guarantee a successful fallback to `xelatex`.
- Expand language mappings in the LLM prompts generator to correctly format all supported languages.
- Update the in-memory task configuration (specifically `source_language`, `target_language`, and `advanced_config`) *before* persisting the task to Supabase in both the single translation and batch translation routes.
- Enhance the `update_task` method in the task manager to support updating `source_language` and `target_language` and syncing them to the database.

## Impact
- Affected specs: translation-history, latex-translation-core
- Affected code: `task_manager.py`, `translate.py`, `reconstruct.py`, `prompts.py`, `utils.py`, `compiler.py`

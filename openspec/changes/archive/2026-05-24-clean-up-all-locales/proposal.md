# Change: Clean Up and Professionalize All Locales

## Why
The maintained locale files had drifted in tone and quality, with some interactive prompts still ending in question marks and some target-language entries still carrying English fallback or placeholder corruption. This change restored the shipped locale set to a consistent, professional state.

## What Changes
- Rewrote interactive prompts into declarative copy across the maintained locales.
- Preserved proper nouns such as `PaperX`, `arXiv`, `PaperTool`, and `paper copilot` in their established forms.
- Replaced English fallback text and placeholder corruption with target-language copy for `en`, `de`, `es`, `fr`, `ja`, `ko`, and `ru`.

## Impact
- Affected spec: `web-ui`
- Affected files: `frontend/src/locales/en/common.json`, `frontend/src/locales/de/common.json`, `frontend/src/locales/es/common.json`, `frontend/src/locales/fr/common.json`, `frontend/src/locales/ja/common.json`, `frontend/src/locales/ko/common.json`, `frontend/src/locales/ru/common.json`

## Verification
- Run `Select-String "[?锛焆"` across `frontend/src/locales`.
- Verify JSON syntax for all locale files.
- Review the modified locale entries for tone and translation consistency.

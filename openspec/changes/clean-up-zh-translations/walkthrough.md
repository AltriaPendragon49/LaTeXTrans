# Walkthrough: Clean Up ZH Translations

## Changes Made

### 1. Translation File Update
- File: [common.json](file:///d:/future/antigravity/LaTexTrans/frontend/src/locales/zh/common.json)
- **Deep Clean of Question Marks**: Removed both half-width (?) and full-width (？) question marks.
  - Specifically targeted the `insights` section (Section Problem, Solution, Innovation, etc.) which contained full-width question marks.
  - Converted confirmation prompts to assertive statements.
- **Placeholder Removal**: 
  - Replaced all `????` placeholders in the Community Admin Task management section.
  - Cleaned up `community.feed.searchPlaceholder` by removing the `（占位）` tag and replacing it with professional search instructions.
- **Proper Noun Preservation**: 
  - Preserved `PaperTool` as a proper noun (reverted from "论文工具" per user's manual preference).
  - Kept `PaperX`, `arXiv`, `PDF`, `Niutrans`, `Week 1`, and `paper copilot`.

### 2. Specification Update
- File: [spec.md](file:///d:/future/antigravity/LaTexTrans/openspec/specs/web-ui/spec.md)
- Updated the `Locale-managed PaperX copy stays language-aligned` scenario to strictly forbid all forms of question marks and placeholder corruption.

## Verification Results
- **Global Search**: Handled via `Select-String "[?？]"` and confirmed 0 matches.
- **Placeholder Check**: Confirmed no `??` or `????` sequences remain.
- **Contextual Accuracy**: Ensured translations for task management items (queued, processing, completed, failed) are natural and consistent with the rest of the UI.

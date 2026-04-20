# Plan: Clean Up and Professionalize All Locales

This plan aims to synchronize the professional tone of all localization files with the recently updated Chinese locale. Specifically, it involves removing question marks from active UI prompts and translating all English fallbacks or placeholder corruption into the respective target languages.

## User Review Required

> [!IMPORTANT]
> - **Tone Shift**: All interactive questions (e.g., "Confirm delete?") will be converted to declarative statements (e.g., "Confirm deletion.") in all languages.
> - **Proper Nouns**: Proper nouns like `PaperX`, `arXiv`, `PaperTool`, `paper copilot`, etc., will remain in English or their established branding form across all locales.
> - **Translation Accuracy**: I will provide translations for `en`, `de`, `es`, `fr`, `ja`, `ko`, and `ru`. While I strive for native-level accuracy, specific cultural nuances for "professional assertive tone" in these languages will be prioritized.

## Proposed Changes

### [Localization Component]

#### [MODIFY] [en/common.json](file:///d:/future/antigravity/LaTexTrans/frontend/src/locales/en/common.json)
- Remove question marks from interactive prompts and the `insights` section.
- **Example**: `Continue?` -> `Proceed with deletion.`
- **Example**: `What problem does this paper solve...` -> `Problem description, significance, and key gaps.`

#### [MODIFY] [de/common.json](file:///d:/future/antigravity/LaTexTrans/frontend/src/locales/de/common.json)
- Remove question marks and translate English fallbacks.
- **Example**: `Löschen?` -> `Löschen bestätigen.`
- **Tone**: Formal and declarative.

#### [MODIFY] [es/common.json](file:///d:/future/antigravity/LaTexTrans/frontend/src/locales/es/common.json)
- Remove question marks and translate English fallbacks.
- **Example**: `¿Eliminar?` -> `Confirmar eliminación.`
- **Tone**: Clear and assertive.

#### [MODIFY] [fr/common.json](file:///d:/future/antigravity/LaTexTrans/frontend/src/locales/fr/common.json)
- Remove question marks and translate English fallbacks.
- **Example**: `Supprimer ?` -> `Confirmer la suppression.`
- **Tone**: Professional and direct.

#### [MODIFY] [ja/common.json](file:///d:/future/antigravity/LaTexTrans/frontend/src/locales/ja/common.json)
- Remove question marks and translate English fallbacks.
- **Example**: `削除しますか？` -> `削除を実行します。`
- **Tone**: Standard polite declarative (Desu/Masu) or professional neutral.

#### [MODIFY] [ko/common.json](file:///d:/future/antigravity/LaTexTrans/frontend/src/locales/ko/common.json)
- Remove question marks and translate English fallbacks.
- **Example**: `삭제하시겠습니까?` -> `삭제를 진행합니다.`
- **Tone**: Formal declarative.

#### [MODIFY] [ru/common.json](file:///d:/future/antigravity/LaTexTrans/frontend/src/locales/ru/common.json)
- Remove question marks, translate English fallbacks, and fix `????` corruption.
- **Example**: `Удалить?` -> `Подтверждение удаления.`
- **Tone**: Professional and concise.

## Verification Plan

### Automated Tests
- Run `Select-String "[?？]"` across the `frontend/src/locales` directory to ensure no question marks remain.
- Scan for strings starting with `??` or containing exclusively English fallback patterns in non-English locales.

### Manual Verification
- Review the modified JSON files for structural integrity and translation consistency.

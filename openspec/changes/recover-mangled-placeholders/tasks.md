# Tasks: recover-mangled-placeholders

## 1. Placeholder Recovery Utilitity
- [x] 1.1 Add `restore_mangled_placeholders(tex_content, expected_phs)` in `backend/app/services/latex/utils.py`.
- [x] 1.2 Generate flexible regex patterns capable of matching variants introduced by LLMs (e.g. `\textless PLACEHOLDER\_ENV\_1\textgreater`, `<$PLACEHOLDER_CAP_1$>`).

## 2. Integration into Compilation Flow
- [x] 2.1 Invoke `_restore_mangled_placeholders(tex)` inside `LatexConstructor.construct()` after building the combined section string.
- [x] 2.2 Ensure the method collects exactly which keys from `envs`, `captions`, `newcommands`, and `inputs` need restoration.
- [x] 2.3 Invoke `restore_mangled_placeholders` at the start of `TranslatorAgent._fix_missing_placeholders` to correct placeholders in translated text before missing tag matching occurs.

## 3. Unit Tests and Verification
- [x] 3.1 Create targeting specific scenarios like math mode escaping and angle bracket escapes in `backend/tests/unit/services/latex/test_placeholders.py`.
- [x] 3.2 Run the full pytest suite (`tests/`) to guarantee no regressions in standard `replace()` matching.
- [x] 3.3 Ensure the exact placeholder versions are not doubly processed if they appear natively correct.

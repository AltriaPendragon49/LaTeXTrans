## 1. Specification
- [x] 1.1 Add OpenSpec requirements for the parity-safe enhancement branch.
- [x] 1.2 Validate the OpenSpec change in strict non-interactive mode.

## 2. Compiler Architecture
- [x] 2.1 Remove direct bare-percent source mutation from the baseline origin CLI parity compile path.
- [x] 2.2 Add an internal temporary-project enhancement branch for `compile_with_origin_cli_parity()`.
- [x] 2.3 Keep baseline PDF selection and task status semantics unchanged.
- [x] 2.4 Ensure enhanced branch failures are non-fatal and always fall back to baseline.

## 3. Health Repairs
- [x] 3.1 Run bare `%` citation-precompile repair only in the enhanced copy.
- [x] 3.2 Apply `_prepare_bibliography_inputs()` to parity branch `latexmk` commands.
- [x] 3.3 Gate `_fallback_biblatex_to_thebibliography()` to matching biblatex/no-real-bib conditions inside the enhanced copy.
- [x] 3.4 Apply pdfTeX primitive cleanup and CJK helpers in the enhanced copy.
- [x] 3.5 Apply precompile package sanitization in the enhanced copy.
- [x] 3.6 Retry image sanitizer only after image-related compile-log triggers.
- [x] 3.7 Confirm translated PDF leading-blank-page normalization remains delivery-only and non-fatal.

## 4. Tests
- [x] 4.1 Add regression coverage proving baseline compile does not mutate source files.
- [x] 4.2 Add regression coverage proving bare `%` repair succeeds only through the enhanced branch.
- [x] 4.3 Add regression coverage proving branch failure returns the baseline PDF.
- [x] 4.4 Add regression coverage for bibliography input flags in parity branch commands.
- [x] 4.5 Run focused backend compiler/parity tests.

## 5. Deployment Verification
- [ ] 5.1 Commit the implementation.
- [ ] 5.2 Deploy to the production server.
- [ ] 5.3 Start admin curation translation for `1910.10683` and confirm the enhanced branch repairs the citation/pre-bibliography compile issue.
- [ ] 5.4 Compare `1910.10683` output against `NiuTrans/LaTeXTrans/outputs/zh_1910.10683` for the expected citation/PDF behavior.
- [ ] 5.5 Start admin curation translation for `2508.15260` and confirm non-triggering tasks preserve baseline behavior.

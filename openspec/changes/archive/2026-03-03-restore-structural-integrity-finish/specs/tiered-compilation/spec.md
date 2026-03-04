# Spec: latex-translation-core

## ADDED Requirements

### Requirement: Non-Invasive Default Compilation
The compiler MUST default to execution via `latexmk` (Stage 0) without any modification to the user's source files, `.cls` bundles, or bibliography files.

#### Scenario: Standard build
1. Given a standard arXiv project with bundled `IEEEtran.cls`.
2. When compilation starts
3. Then the compiler MUST NOT delete or replace `IEEEtran.cls` before attempting the pure `latexmk` run.

### Requirement: Degraded Invasive Compilation
Only if Stage 0 (pristine) and Stage 1 (minimal shims) fail, the compiler MAY step into Stage 2 (invasive), where it deletes outdated `.cls` files or replaces `biblatex` with `thebibliography`. The result MUST be explicitly marked as degraded.

#### Scenario: Pristine build fails due to old biblatex
1. Given Stage 0 and 1 failed with biblatex errors.
2. When Stage 2 is triggered
3. Then it replaces the `biblatex` macros, runs compilation, and logs a clear degraded warning along with a diff of modifications.

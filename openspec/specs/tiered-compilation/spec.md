# tiered-compilation Specification

## Purpose
TBD - created by archiving change restore-structural-integrity-finish. Update Purpose after archive.
## Requirements
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

### Requirement: Stage 3 Sanitizer Execution Invariance
Stage 3 image sanitizer behavior implemented in the compiler MUST remain reachable through compile-failure image-error flow and MUST NOT be bypassed by orchestration refactors.

#### Scenario: Image-related compile failure still enters Stage 3
1. Given compilation failure logs include image-related signatures (for example `(pdf inclusion)` / `reading image failed`)
2. When fallback selection proceeds to Stage 3
3. Then the compiler MUST invoke the existing Stage 3 sanitizer entrypoint
4. And this change MUST NOT relocate sanitizer execution into external orchestration nodes.

#### Scenario: Multiline image-error variant triggers Stage 3
1. Given image-related log fragments are split across wrapped lines
2. When Stage 3 trigger detection runs
3. Then trigger detection MUST still enter Stage 3 sanitizer flow.

### Requirement: CJK Final PDF Selection Preference
The compiler SHALL prefer `xelatex` as the final artifact source for CJK outputs whenever `xelatex` successfully produces a PDF.

#### Scenario: CJK document has both XeLaTeX and LuaLaTeX PDFs
- **WHEN** a CJK task reaches final PDF selection
- **AND** both `xelatex` and `lualatex` produced candidate PDFs
- **THEN** the final selected PDF MUST prefer the `xelatex` artifact
- **AND** `lualatex` MAY remain as a fallback candidate only when `xelatex` failed to produce a PDF.


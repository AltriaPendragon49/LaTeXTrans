## ADDED Requirements

### Requirement: Origin CLI Parity Health Enhancement Branch
The origin CLI parity compiler SHALL preserve the legacy parity compile path as a baseline while allowing targeted LaTeX health repairs to run only in a temporary enhanced project copy.

#### Scenario: Baseline compile remains immutable
- **WHEN** an `origin_cli_parity` task enters PDF compilation
- **THEN** the baseline compilation SHALL use the legacy parity engine order of `pdflatex` first and `xelatex` only when no `pdflatex` PDF exists
- **AND** the baseline compilation SHALL NOT mutate source `.tex`, `.cls`, `.sty`, or bibliography files with health repair transformations before running.

#### Scenario: Enhanced branch is discardable
- **WHEN** a parity health enhancement branch is attempted
- **THEN** the branch SHALL operate on a temporary copy of the translated LaTeX project
- **AND** failures, exceptions, timeouts, or no-PDF results in the branch SHALL NOT change the baseline result
- **AND** the task SHALL return the baseline PDF when one exists.

#### Scenario: Enhanced PDF adoption is constrained
- **WHEN** the enhanced branch produces a PDF
- **AND** the baseline produced no PDF or the branch repaired a recognized health trigger
- **THEN** the system MAY return the enhanced PDF as the task artifact
- **AND** it SHALL preserve existing task status semantics and MUST NOT mark a previously successful baseline task as failed.

#### Scenario: Modern protection systems remain disabled
- **WHEN** the health enhancement branch runs for an `origin_cli_parity` task
- **THEN** it SHALL NOT invoke hard-freeze, structure guard, post-compile target-language fallback, residual-English fallback, controlled repair, ultimate downgrade, or intelligent multi-engine selection.

### Requirement: Origin CLI Parity Targeted Health Repairs
The parity health enhancement branch SHALL only apply deterministic LaTeX/PDF health repairs with bounded triggers and rollback through the temporary copy.

#### Scenario: Bare percent repair runs in enhanced copy
- **WHEN** translated text contains a recognized unescaped `%` risk inside a supported text macro such as `\texttt{...}`
- **THEN** the health branch SHALL escape the bare percent only in the temporary copy before compiling
- **AND** the baseline source file SHALL remain unchanged.

#### Scenario: Bibliography inputs are prepared for parity latexmk
- **WHEN** the parity compiler runs `latexmk` in the baseline or enhanced path
- **THEN** it SHALL choose the BibTeX flag using project bibliography inputs, using real `.bib` files when present
- **AND** the baseline path SHALL NOT restore or rewrite bibliography files while making that flag decision
- **AND** manual `.bbl` restoration MAY run only inside the temporary enhanced copy
- **AND** this decision SHALL NOT by itself convert warning-level citation diagnostics into task failure.

#### Scenario: Invasive bibliography fallback is branch-only
- **WHEN** a project uses `biblatex`, has no real `.bib` files, and contains an older compatible `.bbl` fallback candidate
- **THEN** the health branch MAY replace `\printbibliography` with a generated `thebibliography` block in the temporary copy
- **AND** this fallback SHALL NOT modify the baseline project files.

#### Scenario: CJK and pdfTeX primitive repairs are branch-only
- **WHEN** a CJK parity project or its compile logs match supported pdfTeX primitive, CJK math-family, CJK dummy-environment, local font-package, or page-overflow health triggers
- **THEN** the health branch MAY apply the corresponding deterministic repair in the temporary copy
- **AND** failure of those repairs SHALL fall back to baseline output.

#### Scenario: Image sanitizer is log-triggered
- **WHEN** parity compilation logs contain image-related failures such as `pdf inclusion` or `reading image failed`
- **THEN** the health branch MAY sanitize the affected included PDF images and patch `\includegraphics` only in the temporary copy
- **AND** sanitizer failure SHALL fall back to baseline output or the original failure result.

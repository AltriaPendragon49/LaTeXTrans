# latex-translation-core Delta

## MODIFIED Requirements

### Requirement: LaTeX Compilation with Intelligent Fallback
The system SHALL compile translated LaTeX files with intelligent multi-engine fallback and MUST produce explicit structured outcomes for success and compilation failure.

#### Scenario: Timeout process-tree cleanup
- **WHEN** a compile subprocess exceeds timeout
- **THEN** the system MUST terminate the full process tree
- **AND** on Windows MUST use process-tree termination semantics (`taskkill /T /F`).

#### Scenario: Halt on first fatal compile error
- **WHEN** an engine reports a fatal compile error
- **THEN** the system MUST stop the current engine attempt immediately (`-halt-on-error` behavior)
- **AND** continue fallback selection according to engine strategy.

#### Scenario: Outdated local class-file conflict
- **WHEN** a project-bundled `.cls` file conflicts with system TeX distribution compatibility
- **THEN** the system MUST prefer the compatible system class file when safe resolution is available.

#### Scenario: Structured compilation failure result
- **WHEN** all engines fail to produce a valid translated PDF
- **THEN** the generator/coordinator pipeline MUST return structured failure fields including `status=failed_compilation` and `error_summary`
- **AND** MUST persist a `compilation_failed` event in `task_log.json` with diagnostic context.

#### Scenario: Engine fallback PDF path integrity
- **WHEN** multi-engine fallback runs on a project that contains stale pre-copied `<basename>.pdf` or later-engine clobber risk
- **THEN** each engine attempt MUST treat stale `<basename>.pdf` as invalid pre-run output
- **AND** the fallback selector MUST only return `pdf_path` values that still exist on disk at selection time.

#### Scenario: Relative output directory invocation
- **WHEN** compilation is invoked with a relative `output_dir` and engine subprocesses run with `cwd` set to the TeX directory
- **THEN** the compiler MUST normalize `output_dir` and `tex_file` to absolute paths before engine invocation
- **AND** MUST evaluate produced `pdf_path`/`log_path` against the same normalized absolute directory.

#### Scenario: Missing PDF with zero parsed errors
- **WHEN** a compile attempt exits without producing a PDF
- **AND** log parsing returns `error_count=0`
- **THEN** the compiler MUST synthesize a fallback compile error with exit-code context
- **AND** MUST report the compile attempt as failed (not success).

## ADDED Requirements

### Requirement: Display-Math Delimiter Preservation During Reconstruction
The system SHALL preserve source display-math delimiter semantics during reconstruction to avoid invalid math environment combinations.

#### Scenario: Source uses bracketed display math but translation uses dollar delimiters
- **WHEN** source fragment contains `\[` and `\]`
- **AND** translated fragment replaces these with paired `$$`
- **THEN** reconstruction MUST restore paired `$$` back to `\[` and `\]` in order.

#### Scenario: Source does not use bracketed display math
- **WHEN** source fragment has no `\[`/`\]`
- **THEN** the restoration logic MUST NOT force delimiter replacement.

#### Scenario: Unpaired or ambiguous dollar delimiters
- **WHEN** translated fragment contains unmatched/odd `$$`
- **THEN** reconstruction MUST degrade safely (no exception) and preserve remaining text.

#### Scenario: Malformed display-math shell compared with valid source shell
- **WHEN** translated fragment has malformed display-math shell state (e.g., unclosed/mixed `$$`, `\[` and `\]`)
- **AND** the source fragment shell is structurally valid
- **THEN** reconstruction MUST fallback that fragment to source content.

#### Scenario: Inline-math restoration must not capture display math
- **WHEN** inline `$...$` restoration is applied to translated content
- **THEN** the matcher MUST NOT treat `$$...$$` delimiters as inline math boundaries
- **AND** MUST preserve display-math delimiter integrity.

### Requirement: Tag Command Context Preservation During Reconstruction
The system SHALL preserve source `\tag{...}` semantics and MUST prevent translated `\tag` commands from escaping display-math context.

#### Scenario: Source tag dropped by translation
- **WHEN** source fragment contains one or more `\tag{...}` commands
- **AND** translated fragment drops those tags
- **THEN** reconstruction MUST fallback the fragment to source content.

#### Scenario: Translated tag moves outside display-math context
- **WHEN** translated fragment contains `\tag{...}` outside any display-math context
- **AND** source fragment does not contain out-of-context tags
- **THEN** reconstruction MUST fallback the fragment to source content.

#### Scenario: Source has no tag command
- **WHEN** source fragment contains no `\tag{...}` commands
- **AND** translated fragment introduces `\tag{...}`
- **THEN** reconstruction MUST remove those translated tags.

### Requirement: Environment Wrapper and Header-Math Preservation During Reconstruction
The system SHALL preserve source environment shell structure and MUST prevent fatal header-level math token breakage introduced by translation.

#### Scenario: Missing environment begin/end wrappers in translated block
- **WHEN** source fragment is an environment block and translated fragment loses `\begin{env}` or `\end{env}`
- **THEN** reconstruction MUST restore source-compatible begin/end wrappers around the translated body
- **AND** MUST keep translated body content whenever non-empty.

#### Scenario: Unsafe translated environment header after math delimiter loss
- **WHEN** source environment header contains inline math delimiters
- **AND** translated header drops delimiters and leaves unsafe `_` or `^` tokens
- **THEN** reconstruction MUST first attempt translated-header repair by wrapping math-like tokens into inline math
- **AND** MUST fallback to the source begin-header command only if translated header remains unsafe.

#### Scenario: Wrapper repair fallback when translated body is empty
- **WHEN** wrapper restoration is required and translated body content is empty
- **THEN** reconstruction MUST fallback to the source body content to keep environment syntactically valid.

#### Scenario: Unsafe translated inner environment wrapper
- **WHEN** translated environment content is fully wrapped by a non-ASCII/unsafe inner `\begin{...}` `\end{...}` pair
- **THEN** reconstruction MUST strip the unsafe inner wrapper
- **AND** MUST preserve the translated body text inside the original source-compatible outer environment.

### Requirement: Sectioning Command-Structure Preservation During Reconstruction
The system SHALL preserve sectioning command shells and MUST repair unsafe heading math-token drift introduced by translation.

#### Scenario: Sectioning command sequence mismatch
- **WHEN** source and translated fragments contain different sectioning command sequences (`\section`, `\subsection`, etc.)
- **THEN** reconstruction MUST fallback the section fragment to source content.

#### Scenario: Malformed sectioning command argument structure
- **WHEN** translated sectioning commands have malformed required argument groups
- **THEN** reconstruction MUST fallback the section fragment to source content.

#### Scenario: Source heading contains math but translated heading drops delimiters
- **WHEN** source heading argument contains inline math
- **AND** translated heading argument drops `$...$` but contains unsafe `_`/`^` tokens
- **THEN** reconstruction MUST first attempt to wrap likely math tokens with inline delimiters
- **AND** MUST fallback to source heading command only if repaired heading remains unsafe.

### Requirement: Custom Macro Shell Preservation During Reconstruction
The system SHALL preserve argument shells for sensitive custom macro commands used in math papers.

#### Scenario: twopartpiecewise command shell drift
- **WHEN** source fragment contains `\twopartpiecewise{...}{...}{...}{...}`
- **AND** translated fragment keeps command count and placement
- **THEN** reconstruction MUST replace translated command calls with source command calls by occurrence order.

#### Scenario: twopartpiecewise command is dropped or count-mismatched
- **WHEN** translated fragment drops `\twopartpiecewise` commands or changes command count
- **THEN** reconstruction MUST fallback the fragment to source content.

### Requirement: Document Tail Completion Safety
The system SHALL ensure reconstructed output ends with a structurally complete document tail.

#### Scenario: Missing \end{document} with recoverable source anchor
- **WHEN** translated reconstructed content misses `\end{document}`
- **AND** source main tex contains a recoverable late anchor (`\bibliographystyle`, `\bibliography`, `\begin{thebibliography}`, or `\appendix`)
- **THEN** reconstruction MUST splice the source tail from the latest matching anchor.

#### Scenario: Missing \end{document} without recoverable anchor
- **WHEN** translated reconstructed content misses `\end{document}`
- **AND** no safe source anchor can be matched
- **THEN** reconstruction MUST append missing closing braces and `\end{document}` as fallback.

### Requirement: Label-Key Preservation During Reconstruction
The system SHALL preserve source `\label{...}` keys during reconstruction to maintain cross-reference integrity.

#### Scenario: Translated label key is mutated
- **WHEN** translated fragment contains `\label{...}` keys that differ from source keys (e.g., punctuation mutation)
- **THEN** reconstruction MUST restore source label commands deterministically by occurrence order.

#### Scenario: Translated fragment drops labels
- **WHEN** source fragment contains one or more `\label{...}` commands but translated fragment contains none
- **THEN** reconstruction MUST append missing source labels as a safe fallback.

### Requirement: Caption Command-Structure Preservation During Reconstruction
The system SHALL preserve caption command wrappers so translated references remain resolvable.

#### Scenario: Caption command wrapper is dropped in translation
- **WHEN** source caption fragment contains `\caption{...}`, `\subcaption{...}`, or `\captionof{...}{...}`
- **AND** translated caption fragment drops one or more of those command wrappers
- **THEN** reconstruction MUST fallback that caption fragment to source command structure.

#### Scenario: Caption command argument structure is malformed
- **WHEN** translated caption fragment contains caption commands with malformed required argument groups
- **THEN** reconstruction MUST fallback that caption fragment to source command structure.

#### Scenario: Caption command structure remains valid
- **WHEN** translated caption fragment preserves caption command wrappers and valid argument structure
- **THEN** reconstruction MUST keep translated caption content.

### Requirement: API Rate Limit Resilience (429 Handling)
The translation service SHALL handle API rate limits (HTTP 429) gracefully with infinite retry and graduated backoff while maintaining system concurrency.

#### Scenario: Concurrent project isolation during 429 wait
- **WHEN** a translation sub-task hits a 429 error
- **THEN** the system MUST release the global LLM concurrency slot (semaphore) before sleeping
- **AND** MUST resume only after the backoff period expires.

#### Scenario: Graduated backoff strategy
- **WHEN** consecutive 429 errors occur for the same request
- **THEN** the system MUST follow a graduated retry strategy:
  - **Hits 1-3**: Quick retry using `Retry-After` header or default 10s.
  - **Hits 4-9**: Progressive delay (35s to 60s).
  - **Hits >9**: Infinite wait with a fixed 60s interval.

#### Scenario: User notification for persistent rate-limiting
- **WHEN** 429 hits exceed 9 consecutive attempts
- **THEN** the agent MUST push a progress update with a specific rate-limit warning message to the task manager.

#### Scenario: Infinite retry semantics
- **WHEN** a 429 error occurs
- **THEN** the system MUST NOT return the original text or fail the task solely due to rate limits
- **AND** MUST loop until success is achieved or a non-429 fatal error occurs.
 
### Requirement: PDF Page Dimensions and Overflow Prevention for CJK
The system SHALL ensure that translated CJK documents have correct physical page dimensions and MUST prevent content truncation caused by Latin-centric layout packages.

#### Scenario: Replace a4wide with geometry for CJK
- **WHEN** a LaTeX document uses the `a4wide` package (standalone or in a combo `\usepackage{...}`)
- **AND** the target language is a CJK language (zh, ja, ko)
- **THEN** the system MUST replace `a4wide` with `\usepackage[a4paper, left=2cm, right=2cm, top=2.5cm, bottom=2.5cm]{geometry}`
- **OR** if `geometry` is already present, MUST ensure the `a4paper` option is added and `a4wide` is removed.

#### Scenario: Inject raggedbottom for CJK pagination
- **WHEN** the target language is a CJK language (zh, ja, ko)
- **THEN** the system MUST inject `\raggedbottom` before `\begin{document}` to prevent vertical stretching and page overflow.

[Checklist: Delta validation]
- [x] Delimiter restoration covers sections/envs/captions
- [x] Environment wrapper/header-math repair covers env reconstruction path
- [x] Label-key preservation applied in reconstruction path
- [x] 429 handling releases semaphore during sleep
- [x] Backoff strategy is graduated (3 stages)
- [x] Progress updates are emitted after 9 hits
- [x] _fix_page_overflow_for_cjk implemented in utils.py
- [x] a4wide combo-package replacement handled correctly
- [x] \raggedbottom injected correctly for CJK
- [x] Display-math shell malformed fallback integrated in reconstruction
- [x] Out-of-context \tag detection and fallback integrated
- [x] Sectioning command-shell repair integrated
- [x] \twopartpiecewise shell restoration integrated
- [x] Document-tail restoration integrated before final write
- [x] Inline-math regex excludes $$...$$ display blocks
- [x] No-PDF/0-error fallback compile normalization implemented

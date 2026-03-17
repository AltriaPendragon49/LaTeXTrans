## MODIFIED Requirements

### Requirement: LaTeX Parsing and Translation
The system SHALL parse LaTeX source files into an Abstract Syntax Tree (AST), translate extracted text content while preserving structure, and reconstruct valid LaTeX output. **The system SHALL algorithmically enforce a maximum token length for all textual sections before transmission to the Language Model.**

#### Scenario: Immutable placeholder chunk passthrough
- **WHEN** parser chunking produces a section fragment that contains only immutable placeholders or no translatable natural-language payload
- **THEN** the system MUST mark the chunk as immutable
- **AND** MUST bypass language-model translation for that chunk
- **AND** MUST preserve the chunk content verbatim during reconstruction and later repair stages.

#### Scenario: Generic text environment wrapper preservation
- **WHEN** the system translates a generic text environment such as `abstract`, `quote`, `quotation`, `remark`, `proof`, `definition`, `example`, `theorem`, `lemma`, `proposition`, or `corollary`
- **THEN** it MUST preserve the source `\begin{...}` and `\end{...}` wrapper exactly
- **AND** MUST translate only the environment body
- **AND** MUST reject any final environment output that still contains synthetic `ENV_BEGIN` or `ENV_END` markers.

#### Scenario: Synthetic placeholder transport protection
- **WHEN** section or environment payloads contain synthetic placeholders such as `<PLACEHOLDER_...>`, `<ENV_...>`, `<ENV_BEGIN_...>`, `<ENV_END_...>`, `<ITEM_...>`, or `<EQROW_...>`
- **THEN** the system MUST mask those placeholders before sending the payload to the language model
- **AND** MUST restore the exact original placeholder tokens after the model response is received
- **AND** MUST prevent translated placeholder names from entering reconstructed LaTeX output.

#### Scenario: Structural preamble commands remain immutable during transport
- **WHEN** a document-root or preamble payload contains structural commands such as `\documentclass{...}`, `\usepackage{...}`, `\RequirePackage{...}`, `\input{...}`, `\include{...}`, `\bibliographystyle{...}`, or `\bibliography{...}`
- **THEN** the system MUST protect the entire command and its arguments before sending the payload to the language model
- **AND** MUST restore the exact original command text after the model response is received
- **AND** MUST NOT allow package names, bibliography/style identifiers, or included file names to be translated, escaped, or reordered.

#### Scenario: Residual structure token masking
- **WHEN** a section or retry payload still contains residual raw structure tokens such as `\begin{...}`, `\end{...}`, or lone `$` after normal math/environment isolation
- **THEN** the system MUST mask those residual tokens before payload invariants are checked
- **AND** MUST restore the exact original tokens after the model response is received
- **AND** MUST NOT downgrade the segment to raw source solely because the residual tokens crossed a chunk boundary.

#### Scenario: Display math stays protected during payload preparation
- **WHEN** a section or retry payload contains display-math spans such as `$$...$$` or `\[...\]`
- **THEN** the system MUST isolate those spans before payload invariant checks run
- **AND** MUST restore the exact original display-math spans after the language-model response is received
- **AND** MUST NOT classify the segment as payload-invariant passthrough solely because display-math delimiters exposed raw dollar tokens.

#### Scenario: Structure shell extraction and reattachment
- **WHEN** a section chunk contains leading or trailing structure shell material such as boundary `\begin{...}` / `\end{...}` tokens, page-break commands, or placeholder atoms adjacent to prose
- **THEN** the parser MUST record `leading_structure_shell`, `core_translatable_content`, and `trailing_structure_shell`
- **AND** the translator MUST send only `core_translatable_content` to the language model
- **AND** the translator MUST reattach the recorded structure shells verbatim around the translated core.

#### Scenario: Structure-shell-only chunk passthrough
- **WHEN** a section chunk contains only structure shell material and no translatable prose core
- **THEN** the system MUST mark the chunk as immutable passthrough
- **AND** MUST preserve the chunk verbatim through translation, repair, and generation stages.

#### Scenario: Source preservation on env restore failure
- **WHEN** a translated section or list environment still contains `<ENV_RESTORE_FAILED>` or unresolved synthetic `ENV` markers after post-processing
- **THEN** the system MUST replace that segment with the original source content
- **AND** MUST record fallback metadata for the affected segment
- **AND** MUST NOT allow the unresolved synthetic markers to reach reconstructed project files.

#### Scenario: Generic text env retries before source fallback
- **WHEN** a generic text environment body translation leaks synthetic env markers after the first restoration attempt
- **THEN** the system MUST perform one targeted retry with an explicit restoration-correction hint
- **AND** MUST keep the source wrapper unchanged across both attempts
- **AND** MUST preserve the original source content only if the retry still leaves unresolved synthetic env markers.

#### Scenario: Abstract-like envs must prefer target-language recovery
- **WHEN** a generic text environment such as `abstract` still remains in source language after the primary env-translation path fails
- **AND** the wrapper can still be preserved safely
- **THEN** the system MUST attempt a stronger target-language recovery path for the environment body before preserving source text
- **AND** MUST keep the original `\begin{...}` / `\end{...}` wrapper unchanged
- **AND** MUST only preserve the original source body when every safe recovery path fails structural checks.

#### Scenario: Final PDF must not accept unresolved natbib citations
- **WHEN** a compilation candidate PDF is produced but the corresponding LaTeX log still contains natbib undefined-citation warnings
- **THEN** the pipeline MUST treat that result as bibliographically unresolved rather than a perfect compilation
- **AND** MUST continue recompilation / selection logic instead of immediately finalizing that PDF
- **AND** MUST NOT choose a final PDF whose rendered citations are expected to appear as `(?)` or `(??)` when a recoverable bibliography pass is still possible.

#### Scenario: Payload invariant passthrough tracking
- **WHEN** a section is preserved via payload invariant protection instead of network/API failure
- **THEN** the system MUST record a dedicated passthrough status distinct from generic API fallback
- **AND** MUST NOT classify that section as a no-op translation retry
- **AND** MUST expose the affected section in audit and task-log metadata.

#### Scenario: Long English prose rejection
- **WHEN** a translated body section still contains a long contiguous English prose span that exceeds the completeness threshold
- **THEN** the validator MUST classify the section as a recoverable completeness failure
- **AND** MUST request a targeted retry that preserves LaTeX commands, placeholders, math, and structure shells
- **AND** MUST NOT silently accept the untranslated prose block into the final output.

#### Scenario: Structure guard warning on macro-body env tokens
- **WHEN** the assembled LaTeX project contains environment tokens inside macro-definition argument bodies or title/author templating hooks
- **AND** the document otherwise has no unresolved placeholders or hard structural corruption
- **THEN** precompile structure checking MUST classify the condition as warning-only
- **AND** the pipeline MUST continue into compilation instead of aborting before compile.

#### Scenario: Post-compile fallback after successful compile
- **WHEN** compile fallback reports exist after generation
- **AND** post-compile target-language fallback is enabled
- **AND** the fallback node has not yet been attempted
- **THEN** the pipeline MUST run the post-compile fallback node once even if the initial compile already produced a PDF
- **AND** MUST log both fallback start and fallback completion events before regenerating output.

#### Scenario: Section fallback must survive reconstruction
- **WHEN** a section chunk is rewritten by `ultimate downgrade` or post-compile target-language fallback
- **THEN** the section output written into the final reconstructed `.tex` MUST preserve target-language body content
- **AND** MUST NOT revert the full section block to source-language text solely because section wrapper restoration detected a mismatch
- **AND** MUST continue to support starred section wrappers such as `\section*{...}` and `\subsection*{...}` during reconstruction
- **AND** MUST preserve any internal structure tokens embedded inside the fallback section body, including placeholders, environment boundaries, page-break commands, and lettrine-style commands, whenever those tokens were already present in the translated body
- **AND** the audit pipeline MUST be able to detect any long English prose that still survives in the final main `.tex`.

#### Scenario: Readable fallback around formulas and references
- **WHEN** section fallback rewrites target-language prose that is adjacent to inline math, citations, references, footnotes, links, or common text-formatting commands
- **THEN** the fallback renderer MUST preserve those safe inline LaTeX constructs verbatim
- **AND** MUST NOT degrade them into escaped literal text such as `\textasciitilde{}`, `\textbackslash{}`, or `\$...\$`
- **AND** MUST keep the surrounding downgraded prose compilable and readable in the target language.

#### Scenario: Document-root compile-first chunks stay source-safe on retry
- **WHEN** a document-root section chunk is marked as compile-first structural fallback pending compile
- **AND** post-compile target-language fallback decides to skip deterministic rewriting for that chunk
- **THEN** the subsequent regenerate pass MUST preserve the chunk's source-safe content for compilation
- **AND** MUST NOT reuse a broken translated payload that omits `\documentclass`, `\documentstyle`, or protected preamble commands
- **AND** the compiler MUST still be able to detect the main TeX entry file after the retry handoff.

#### Scenario: Deterministic fallback preserves paragraph boundaries and paragraph-head macros
- **WHEN** deterministic section fallback rewrites target-language prose that contains paragraph-heading macros such as `\PAR{...}`, `\PARR{...}`, `\parhead{...}`, `\parheadno{...}`, or `\parheadsc{...}`
- **OR** contains preserved structure tokens such as `\label{...}`, references, or section transitions adjacent to prose
- **THEN** the fallback renderer MUST preserve those paragraph-heading macros verbatim
- **AND** MUST preserve paragraph or blank-line boundaries around preserved commands so they do not collapse into adjacent prose
- **AND** MUST NOT concatenate labels, paragraph headings, or section boundaries directly onto neighboring text during reconstruction.

#### Scenario: Generic text env retries after source-fallback first attempt
- **WHEN** a generic text environment such as `abstract` receives a first-pass translation result that falls back to unchanged source text because of API failure or payload invariant protection
- **AND** no leaked env-marker artifact is present in that returned text
- **THEN** the pipeline MUST still attempt one plain-text body recovery retry before preserving the source environment body
- **AND** MUST preserve the source environment wrapper around any recovered target-language body
- **AND** MUST NOT immediately accept unchanged English source text when a safe target-language retry path remains available.

#### Scenario: Deterministic fallback preserves bibliography commands and semantic custom macros
- **WHEN** deterministic section fallback rewrites target-language prose that contains bibliography handoff commands such as `\bibliography{...}`, `\bibliographystyle{...}`, `\addbibresource{...}`, or `\printbibliography`
- **OR** contains safe semantic inline custom macros used as domain terminology or abbreviations
- **THEN** the fallback renderer MUST preserve those commands verbatim whenever they are not document-root or package-loading structure
- **AND** MUST NOT erase semantic macro tokens into blank gaps in the downgraded target-language prose
- **AND** MUST preserve bibliography handoff commands so later compilation stages can still resolve citations.

#### Scenario: Chunked document-root sections stay source-safe
- **WHEN** the parser emits a chunked document-root section such as `-1_chunk_1`
- **OR** any section marked with `chunk_role = document_root`
- **THEN** the translation dispatcher MUST treat that chunk as source-safe passthrough rather than normal translatable prose
- **AND** MUST preserve the original document-root content verbatim in `trans_content`
- **AND** MUST NOT allow LLM explanatory chatter or translated prose to appear before `\documentclass`, `\documentstyle`, or protected preamble commands in the regenerated TeX.

#### Scenario: Deterministic fallback preserves `\maketitle` in first-body chunks
- **WHEN** deterministic section fallback rewrites a first-body chunk whose leading shell begins with `\begin{document}`
- **AND** the original chunk body still contains `\maketitle` before the first translated section command
- **THEN** the fallback renderer MUST preserve `\maketitle` verbatim in the reconstructed output
- **AND** MUST keep the first rendered title / teaser / abstract block reachable by the final TeX class logic.

#### Scenario: Manual prebuilt `.bbl` workflows do not get erased during compile
- **WHEN** a project manually includes bibliography content with `\input{...bbl}` or `\include{...bbl}`
- **AND** the TeX source does not provide a BibTeX / BibLaTeX driver such as `\bibliography{...}`, `\addbibresource{...}`, or `\printbibliography`
- **THEN** the compile pipeline MUST NOT run BibTeX in a way that overwrites the prebuilt `.bbl` with an empty file
- **AND** MUST restore or preserve available prebuilt bibliography artifacts before compilation when necessary
- **AND** the resulting compile MUST still be able to resolve citation keys into bibliography references rather than `(?)`.

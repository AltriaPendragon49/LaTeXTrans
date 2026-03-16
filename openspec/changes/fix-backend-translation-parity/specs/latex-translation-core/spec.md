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

#### Scenario: Residual structure token masking
- **WHEN** a section or retry payload still contains residual raw structure tokens such as `\begin{...}`, `\end{...}`, or lone `$` after normal math/environment isolation
- **THEN** the system MUST mask those residual tokens before payload invariants are checked
- **AND** MUST restore the exact original tokens after the model response is received
- **AND** MUST NOT downgrade the segment to raw source solely because the residual tokens crossed a chunk boundary.

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

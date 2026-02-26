# latex-translation-core Delta

## MODIFIED Requirements

### Requirement: LaTeX Parsing and Translation

The system SHALL parse LaTeX source files into an Abstract Syntax Tree (AST), translate extracted text content while preserving structure, and reconstruct valid LaTeX output. **The system SHALL algorithmically enforce a maximum token length for all textual sections before transmission to the Language Model.**

#### Scenario: Single huge section chunking (NEW)
- **WHEN** a LaTeX document parsing yields a section whose content exceeds a predefined maximum token threshold (e.g., 4000 tokens)
- **THEN** the system SHALL divide the section into sequential sub-chunks
- **AND** the split SHALL primarily occur at natural paragraph boundaries (double newlines) to preserve semantic contexts natively
- **AND** the sub-chunks SHALL independently undergo translation without exceeding language model token limits.

#### Scenario: Extreme single paragraph fallback (NEW)
- **WHEN** an individual natural paragraph internally exceeds the maximum token threshold
- **THEN** the system SHALL apply a secondary splitting heuristic using sentence-terminating punctuation
- **AND** prioritize maintaining semantic integrity over exact character limits.

#### Scenario: Cross-chunk context preservation (Overlap context) (NEW)
- **WHEN** a section block is algorithmically divided into sequential sub-chunks
- **THEN** the system MUST extract the trailing segment (e.g., the last paragraph or sentence) of a preceding chunk
- **AND** pass it as read-only "Reference Context" to the language model when translating the subsequent chunk
- **AND** instruct the model to strictly ignore this context for output generation to prevent duplicated translation.

#### Scenario: Reference Context Prompt Isolation and Leakage Retry (NEW)
- **WHEN** Reference Context is passed to the translation language model
- **THEN** the context MUST be strictly isolated within the `system` prompt role
- **AND** MUST be wrapped in explicit XML tags (e.g., `<REFERENCE_CONTEXT>`)
- **AND** the system MUST execute post-translation validation to detect leaked markup or unmodified context copying
- **AND** if leakage is detected, MUST execute a single retry attempt.

#### Scenario: Context Downgrade Fallback (NEW)
- **WHEN** a translation sub-chunk triggers leakage detection repeatedly (failing the retry attempt)
- **THEN** the system MUST downgrade the translation request by structurally stripping the Reference Context from the prompt
- **AND** execute a final standalone translation request for the sub-chunk to guarantee compilation safety over contextual flow.

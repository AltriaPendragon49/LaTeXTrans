## MODIFIED Requirements

### Requirement: Public math and caption rendering avoids duplicate or malformed formula output
The system SHALL prefer a single readable math presentation and SHALL not leak broken inline-math fragments or raw LaTeX source commands into prose, captions, tables, or fallback blocks.

#### Scenario: Display math is already renderable in the HTML reader
- **WHEN** a block formula is rendered through the HTML reader math pipeline
- **THEN** the page SHALL show one readable formula presentation
- **AND** it SHALL not leave a second raw horizontal text transcription beside or below the rendered formula.

#### Scenario: A caption or prose fragment contains malformed inline math
- **WHEN** preview generation encounters an unmatched or truncated inline-math fragment such as a dangling `$...`
- **THEN** the reader SHALL repair or remove that malformed fragment from visible prose
- **AND** the page SHALL not expose visibly broken math like `$s_c^{2D`.

#### Scenario: Scholarly formulas or references were split by translation artifacts
- **WHEN** preview generation encounters a display equation, figure caption, or bibliography entry that still contains raw helper commands or is split into multiple broken textual fragments
- **THEN** the reader SHALL normalize those fragments into one readable scholarly presentation
- **AND** it SHALL not expose raw helpers such as `\textbf{}`, `\newblock`, `\natexlab`, or visibly duplicated formula text beside the rendered equation.

#### Scenario: Unknown LaTeX command blocks are not shown as raw source
- **WHEN** preview generation encounters an unsupported environment or command block whose body is primarily raw TeX source
- **THEN** the reader SHALL replace that block with a reader-safe omission note
- **AND** it SHALL not expose raw snippets such as `\begin{tabular}`, `\includegraphics`, or custom macro command text directly in the reading surface.

## ADDED Requirements

### Requirement: Reader-side math hydration has a safe fallback path
The system SHALL keep display math readable even if client-side enhancement hydration partially fails.

#### Scenario: Enhancement pipeline fails but math blocks exist
- **WHEN** the reader receives preview HTML containing `.paper-preview__math-block` nodes and enhancement hydration throws or leaves those blocks unrendered
- **THEN** the client SHALL apply a fallback math renderer for those blocks
- **AND** the paper detail reading flow SHALL remain readable without requiring a full page reload.

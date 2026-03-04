# Spec: latex-translation-core

## ADDED Requirements

### Requirement: Context-Safe Segmentation
Any chunking function (`_chunk_long_sections`) MUST NOT split text if the current parsing pointer is inside an environment (`\begin...\end`) or if the LaTeX brace depth (`{}`) is greater than 0. 

#### Scenario: Long text inside a textbf
1. Given a 2000-character string entirely enclosed in `\textbf{...}`.
2. When the chunker attempts to split it to meet a 1000-token limit
3. Then it MUST NOT split the string, instead warning about an oversize block or skipping translation entirely, ensuring structural invariants are preserved.

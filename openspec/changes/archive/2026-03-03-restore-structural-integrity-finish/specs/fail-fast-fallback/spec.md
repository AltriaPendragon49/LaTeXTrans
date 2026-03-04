# Spec: latex-translation-core

## ADDED Requirements

### Requirement: Removal of Structural Fallback
The translator agent MUST NOT attempt to use regular expressions to stitch natural language back into failed LaTeX structures (`structural_fallback`). If a chunk fails structural validation and exhausts its retries, it MUST fail loudly and gracefully skip translation for that segment or section, retaining the original source.

#### Scenario: Exhausted retries
1. Given an LLM consistently failing to return valid placeholders for 3 retries.
2. When the ultimate failure state is reached
3. Then the translator MUST return the original source LaTeX chunk unchanged and log the exact chunk ID and failure reason, rather than executing a string-based structural repair.

# Change: Implement Context-Aware Smart Section Chunking

## Why
Currently, the system relies on LaTeX structural commands (e.g., `\section`, `\subsection`) to split the document into translatable chunks. However, if a document contains very few or no section commands, the entire text is treated as a single massive section. When sent to the language model, the expected translated output often exceeds the model's `max_new_tokens` limit (e.g., 8192). This leads to catastrophic truncation of the translated text, missing `<PLACEHOLDER_*>` tags, and subsequent fatal LaTeX compilation errors. Simple character-based truncation destroys semantic context and sentence integrity. 

This change introduces a "Context-Aware Smart Section Chunking" mechanism. It intelligently divides oversized sections into smaller, semantically intact chunks using natural boundaries (paragraphs and sentences). Crucially, to prevent referential ambiguity and translation style drift between adjacent chunks, it employs an **Overlap Chunking Pattern**: the tail end of a preceding chunk is passed to the LLM as read-only "Reference Context".

However, LLMs inherently struggle with prompt compliance (e.g., hallucinating or translating the reference context). To mitigate this, the Reference Context will be strictly isolated using XML tags (`<REFERENCE_CONTEXT>`), injected exclusively into the `system` role rather than the `user` role, and subjected to a post-translation leakage detection filter. If leakage occurs, an automated downgrade/retry pipeline guarantees translation completion.

## What Changes
1. **Parser Agent Enhancement**: Modify `LatexParser` in `parser.py` to evaluate the token length of each parsed section after merging short sections.
2. **Natural Boundary Splitting**: For sections exceeding a predefined token threshold (e.g., 4000 tokens), split the `content` string by double newlines (`\n\n`) into paragraphs. If a single paragraph is still too long, fall back to sentence-boundary splitting (e.g., `. `).
3. **Sub-chunk Assembly with Reference Context**: Accumulate these parts into new sub-sections (`sections_json`). When creating a subsequent sub-chunk, inject the last paragraph (or last 500 characters) of the *previous* chunk as a `previous_context` field.
4. **Context-Aware Translation Prompts (High Compliance)**: 
   - Update the System Prompts in `prompts.py` and the LLM request functions in `translator_agent.py` to accept this `previous_context`. 
   - Inject the context **only into the `system` prompt** wrapped in `<REFERENCE_CONTEXT>` XML tags.
   - Instruct the LLM explicitly to strictly translate only the User Prompt and use the XML block purely for stylistic/referential alignment.
5. **Post-Translation Leakage Defense & Downgrade Pipeline**: 
   - After the LLM returns the translated sub-chunk, apply a fast regex/string check for `<REFERENCE_CONTEXT>` tags or direct translations of the context.
   - **Retry Mechanism**: If leakage is detected, the system will execute one immediate retry with the same prompt.
   - **Downgrade Mechanism**: If the retry also fails due to prompt non-compliance, the system will *downgrade* the request: it strips the `previous_context` entirely from the system prompt and sends a standard "standalone string" translation request to guarantee completion without hallucination.
6. **Placeholder Integrity**: The splitting logic ensures that no `<PLACEHOLDER_*>` tags are orphaned or severed.

## Impact
- Affected specs:
  - `latex-translation-core`
- Affected code:
  - `backend/app/services/latex/parser.py`
  - `backend/app/services/agents/translator_agent.py`
  - `backend/app/services/latex/prompts.py`
  - Unit tests in `backend/test/`
- Behavioral outcome:
  - Extreme single-section documents will no longer crash the pipeline by triggering LLM output truncation.
  - The chunking process will maintain semantic continuity natively.
  - LLM hallucinations or context leakage will be self-repaired via the retry-downgrade loop without user intervention, guaranteeing compilation output.

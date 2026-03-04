# Context-Aware Smart Section Chunking Design

## Architecture

The document parsing pipeline in `LatexParser` currently finishes sequence segmentation at `_merge_short_sections`. We will introduce a new step: `_chunk_long_sections(max_tokens: int)`.

### 1. The Chunking Logic (`_chunk_long_sections`)
This method intercepts `self.sections_json`.
For each section:
1. Calculate the token length of `section["content"]` using `tiktoken`.
2. If token length $\le$ `max_tokens`, leave it unchanged.
3. If token length $>$ `max_tokens`:
   - Split `section["content"]` using `\n\n` (natural paragraph boundaries).
   - Track a `previous_chunk_tail` string (holding the last paragraph of the committed chunk).
   - Accumulate paragraphs into a `current_chunk`. When the next paragraph would exceed `max_tokens`, finalize `current_chunk` as a new section entry.
   - For the newly finalized section (if it's not the first sub-chunk), assign `section["previous_context"] = previous_chunk_tail`.
   - Update `previous_chunk_tail` with the end of the newly finalized `current_chunk`.
   - If a single paragraph is larger than `max_tokens`, apply a secondary split by sentence terminators (`. `) to ensure the hard limit is respected, using the same context-carrying mechanism.
   - Ensure the new section IDs indicate their sub-chunk nature (e.g., `"1_chunk_1"`, `"1_chunk_2"`) to maintain correct reassembly order.

### 2. The Translation Prompt Injection (System Role Isolation)
To maximize prompt compliance and prevent the LLM from translating the reference context, we must strictly isolate it.
In `prompts.py`, we add a `previous_context` injection template.
```python
# Pseudo-code representation
if previous_context:
    system_prompt += f"\n<REFERENCE_CONTEXT>\n{previous_context}\n</REFERENCE_CONTEXT>\n\nThe block wrapped in <REFERENCE_CONTEXT> is the tail end of the PREVIOUS section. It is provided ONLY for contextual continuity (e.g., resolving pronouns or terms). DO NOT translate the REFERENCE_CONTEXT. Your output MUST ONLY contain the translated text of the user's input."
```

In `translator_agent.py` (`_translate_section`):
We pass `section.get("previous_context", "")` down to the `_request_llm_for_trans` methods. The payload constructor injects it into the **system** message block dynamically if it exists. The `user` message block contains **only** the text to be translated.

### 3. Post-Translation Leakage Defense & Downgrade Loop
Because LLMs (even in system roles) might occasionally leak XML tags or copy the reference context, we implement a defensive loop in `_translate_section`.

1. **Leakage Detection**: After receiving the LLM output, scan for:
   - Literal `<REFERENCE_CONTEXT>` or `</REFERENCE_CONTEXT>` tags.
   - A high Levenshtein similarity / literal substring match of the English `previous_context` within the translated output (indicating the LLM copied the context verbatim instead of translating the target text).
2. **Retry Route (Level 1)**: If leakage is detected on the first pass, log a warning and automatically execute ONE retry request with the exact same prompt structure.
3. **Downgrade Route (Level 2)**: If the retry attempt *also* fails the leakage detection, a prompt adherence failure is proven. The system will **downgrade** the request:
   - Strip `previous_context` from the section payload entirely in memory.
   - Re-invoke the LLM translation call using the standard, bare system prompt (no XML blocks, no context). This guarantees a clean output for the isolated text block, prioritizing compilation safety over cross-chunk stylistic perfection.

## Trade-offs
- **Pros**: 
  - Resolves semantic drops (e.g., "Therefore, it..." where "it" was defined in the previous chunk).
  - Enforces hard token limits protecting against catastrophic LLM truncation limits.
  - Zero modification to the AST parser `pylatexenc`; operates entirely on the extracted plain text layer.
  - Mitigates prompt non-compliance via systematic retry and downgrade.
- **Cons**: 
  - Marginally higher input token cost (+ ~50-100 tokens per sub-chunk boundary).
  - Downgrades revert behavior to the "naive split" baseline, but only on catastrophic non-compliance events, minimizing risk.

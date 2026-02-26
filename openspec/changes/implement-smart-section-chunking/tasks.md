# Tasks

1. **Parser logic implementation**
   - [ ] In `backend/app/services/latex/parser.py`, add `_chunk_long_sections` method to `LatexParser`.
   - [ ] Implement token counting logic using existing `tiktoken` dependency.
   - [ ] Implement paragraph boundary splitting (`\n\n`) and chunk accumulation.
   - [ ] Implement sentence boundary fallback (`. `) for extremely long single paragraphs.
   - [ ] Implement `previous_context` capturing (saving the last paragraph or sentence of the preceding chunk) and assigning it to the next sub-chunk's dict.
   - [ ] Call `_chunk_long_sections` in `LatexParser.parse()` right after `_merge_short_sections`.

2. **Prompt & Agent enhancement (Anti-Leakage & Downgrade)**
   - [ ] Modify `backend/app/services/latex/prompts.py` to support a `previous_context` injection template wrapped in `<REFERENCE_CONTEXT>` tags.
   - [ ] Modify `backend/app/services/agents/translator_agent.py` (`_translate_section` and `_request_llm_*` methods) to accept `previous_context` and inject it *only* into the `system` role prompt.
   - [ ] Implement leakage detection regex/string checks in `_translate_section` to detect rogue `<REFERENCE_CONTEXT>` tags or copied strings.
   - [ ] Implement the single-retry mechanism when leakage is detected.
   - [ ] Implement the downgrade mechanism (strip `previous_context` and re-translate) when the retry fails.
   
3. **Testing**
   - [ ] Create a unit test `test_parser_chunking.py` verifying that a long section is correctly split and that `previous_context` is correctly assigned to the subsequent chunks.
   - [ ] Create a unit test `test_leakage_downgrade.py` by mocking the LLM response to return leaked `<REFERENCE_CONTEXT>` tags, verifying that the agent successfully executes the retry and downgrade pathways.
   - [ ] Verify that `<PLACEHOLDER_*>` tags remain intact across sentence splits.

4. **Validation**
   - [ ] Run the full pipeline on an oversized LaTeX document and confirm:
         a) No token output truncation occurs.
         b) The compiled PDF maintains paragraph order effortlessly.
         c) Contextual translation flows smoothly across chunk boundaries.
         d) Forced leakage simulations gracefully degrade to standalone translation without crashing.

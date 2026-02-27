# Change: Recover Mangled Placeholders

## Why
During the LaTeX translation process, certain environments, captions, and sensitive commands are masked with placeholders (e.g., `<PLACEHOLDER_ENV_10>`) before being sent to the LLM. 
However, the LLM frequently hallucinates escapes or math-mode wrappings around these placeholders because it interprets them as LaTeX syntax. Examples include:
- `<$PLACEHOLDER_ENV_10$>`
- `\textless PLACEHOLDER\_CAP\_1\textgreater`
- `\langle PLACEHOLDER\_input\_path\_begin \rangle`

Because the downstream reconstruction step (`reconstruct.py`) and the missing placeholder recovery step (`translator_agent.py`) rely on exact string matches or strict regexes (`r"<PLACEHOLDER_[^>]+>"`), these mangled placeholders are entirely missed. 
This results in:
1. Missing environments or captions in the translated output.
2. The mangled placeholders leaking directly into the final compiled PDF as raw, visible text (e.g., `<PLACEHOLDER cNv10>`).

## What Changes
- Add a new `restore_mangled_placeholders` utility function in `backend/app/services/latex/utils.py`.
  - Given a list of expected exact placeholders, it dynamically generates a fuzzy regular expression capable of ignoring common LLM-injected escapes (`\$`, `\_`, `\textless`, `\rangle`, etc.).
  - It searches the translated LaTeX for these fuzzy matches and restores them to their exact, original format.
- Integrate `restore_mangled_placeholders` into `LatexConstructor.construct()` in `reconstruct.py` immediately after sections are merged, ensuring all tags are healed before `replace()` operations attempt to insert the LaTeX bodies.
- Integrate `restore_mangled_placeholders` into `TranslatorAgent._fix_missing_placeholders()` in `translator_agent.py` before it compares the sets of original and translated tags, ensuring missing tag counts are accurate.
- Add targeted unit tests in `tests/unit/services/latex/test_placeholders.py` for the new recovery logic.

## Impact
- Affected specs:
  - `latex-translation-core`
- Affected code:
  - `backend/app/services/latex/utils.py`
  - `backend/app/services/latex/reconstruct.py`
  - `backend/app/services/agents/translator_agent.py`
  - `backend/tests/unit/services/latex/test_placeholders.py`
- Behavioral outcome:
  - Translated PDFs will no longer contain leaked `<PLACEHOLDER_...>` strings.
  - Environments and captions that were previously dropped due to LLM mangling will be successfully reconstructed.
  - The missing placeholder `\input{...}` tag recovery mechanism will no longer trigger false positives or duplicate tags due to mangled syntax.

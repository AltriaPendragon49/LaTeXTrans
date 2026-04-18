# Change: Reinforce target-language fallback priority and pdfTeX-template compatibility

## Why
Recent server runs show a regression where section-level hard-freeze failures now leave large English source sections in the final article (`2006.11239`, `2305.18290`) instead of preserving the strongest available Chinese downgrade. This conflicts with the project's existing target-language-persistence principle and produces a much worse reading experience.

Separately, `2010.11929` fails compilation in Chinese because the source template explicitly pins pdfTeX-oriented driver behavior (for example `\usepackage[pdftex]{graphicx}`), but the translated CJK path currently prefers XeLaTeX/LuaLaTeX.

## What Changes
- Tighten translation fallback behavior so section-level hard-freeze failures must exhaust target-language rescue/downgrade before preserving full source English.
- Make payload-invariant passthrough a last-resort outcome for sections, with explicit rescue accounting and stronger target-language persistence.
- Add compatibility sanitization for explicit pdfTeX driver declarations that break modern CJK engine compilation.
- Add focused regression coverage using the known affected papers/failure families.

## Impact
- Affected specs: `latex-translation-core`, `hard-freeze`
- Affected code: `backend/app/services/agents/translator_agent.py`, `backend/app/services/latex/reconstruct.py`, `backend/app/services/latex/compiler.py`, `backend/app/services/latex/utils.py`, related tests

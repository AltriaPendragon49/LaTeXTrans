# Change: Add Parity-Safe Health Enhancement Branch

## Why
The backend `origin_cli_parity` compiler recently gained a narrow bare-percent citation fix, but applying health fixes directly to the parity source can still perturb tasks that already compile. Production needs a safer way to reuse low-risk LaTeX health repairs while preserving the old parity PDF-success contract.

## What Changes
- Keep the existing origin CLI parity compile path as the immutable baseline: `pdflatex` first, accept any produced PDF, then `xelatex` only if no PDF exists.
- Move direct precompile health mutations, including the existing bare `%` in `\texttt{...}` fix, out of the baseline path and into a temporary enhanced project copy.
- Add a parity health enhancement branch that may try targeted repairs on the temporary copy only, then compile that copy with the same parity engine order.
- Adopt the enhanced PDF only when it produces a PDF and either the baseline produced no PDF or the enhancement branch explicitly repaired a known health trigger.
- Discard the enhanced copy on failure, timeout, or no-PDF output, and return the baseline result without changing task status strategy.
- Restore low-risk health repairs in the branch: bibliography input preparation, targeted biblatex fallback, pdfTeX primitive cleanup, precompile package sanitization, image sanitizer retry, CJK math-family fallback, CJK dummy environments, local `.cls/.sty` font-package patching, and CJK overflow mitigation.
- Do not enable hard-freeze, structure guard, post-compile fallback, residual-English fallback, controlled repair, ultimate downgrade, or intelligent multi-engine selection for parity tasks.

## Impact
- Affected specs: `latex-translation-core`
- Affected code:
  - `backend/app/services/latex/compiler.py`
  - `backend/app/services/latex/utils.py`
  - `backend/app/services/latex/sanitizer.py`
  - `backend/app/services/paper_service.py`
  - backend parity/compiler tests
  - `backend/file.md` if new backend production files are added

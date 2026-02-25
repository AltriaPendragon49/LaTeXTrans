# Change: Fix LaTeX Compilation Resilience and Status Propagation

## Why
The current translation pipeline still has multiple user-visible failure modes:
1. Real LaTeX failures caused by translation rewriting `\[...\]` into `$$...$$`, which breaks environments like `split` and causes fatal compilation errors.
2. Misleading task status semantics where compilation failures can still surface as "completed with warning" plus a generic message (`No PDF file found in output directory`).
3. PDF resolution ambiguity where download/preview logic can accidentally select copied source PDFs instead of translated output PDFs.
4. API Rate Limiting (429) causing incomplete translations or task deadlocks when not handled with proper backoff and concurrency slot release.
5. PDF page overflow/truncation where translated CJK documents (with larger line heights) exceed the physical page boundary when using `a4wide` or similar aggressive layout packages.
6. Additional math-paper regressions from captured snapshots:
   - malformed display-math shells (unbalanced `$$`, mixed `\[...\]` and `$$...$$`) around translated formulas and `\tag`.
   - section title command drift (`\section{...}` argument damage, unsafe `_`/`^` tokens after dropping math delimiters).
   - broken custom math macro calls like `\twopartpiecewise{...}{...}{...}{...}`.
   - truncated document tail that drops bibliography tail or `\end{document}`.
   - false "no compile errors" state when process exits without parsable errors but no PDF is generated.

## What Changes
- Keep the existing compiler hardening work (process cleanup, halt-on-error, outdated `.cls` handling).
- Add deterministic reconstruction-time repair for display-math delimiters:
  - Restore `$$` pairs back to `\[` and `\]` only when the source segment originally used `\[`/`\]`.
  - Apply this repair in sections, environment blocks, and captions before writing translated `.tex`.
- Add strict display-math shell safety repair:
  - Detect malformed display-math shells (odd/unclosed `$$`, shell-mixing imbalance) in translated fragments.
  - Fallback that fragment to source only when source shell is structurally valid.
- Harden `\tag` command safety:
  - Restore dropped source `\tag` commands.
  - Reject translated `\tag` drift that moves tags outside display-math context by fragment fallback.
- Add deterministic reconstruction-time repair for environment shells and unsafe header math:
  - Restore missing `\begin{...}` / `\end{...}` wrappers for translated environment blocks using source wrappers.
  - Preserve translated body content while enforcing source-compatible wrapper structure.
  - Prefer preserving translated (Chinese) headers by wrapping unsafe math-like tokens (e.g., `Y_i`) into inline math.
  - Only fallback to source header command when translated header still contains unsafe `_`/`^` tokens after repair.
  - Strip full-body unsafe translated inner wrappers (e.g., non-ASCII `\begin{定义}...\end{定义}` inside `definition`) while keeping translated body text.
- Add deterministic reconstruction-time repair for caption command shells:
  - Preserve `\caption{...}` / `\subcaption{...}` / `\captionof{...}{...}` command structure from source.
  - If translated caption drops command wrappers or breaks command argument braces, fallback to source caption block for that fragment.
  - Keep translated caption content when command structure remains valid.
- Add deterministic reconstruction-time repair for sectioning command shells:
  - Validate `\section`/`\subsection`/... command sequence and brace structure.
  - Repair unsafe translated title math tokens (e.g., `Y_i`) by inline-math wrapping when source title originally contains math.
  - Fallback to source title command only if translated command remains unsafe after repair.
- Add deterministic reconstruction-time repair for custom macro shell integrity:
  - Restore `\twopartpiecewise{...}{...}{...}{...}` calls from source by occurrence order.
  - Fallback fragment to source if command count mismatches or command is dropped.
- Add deterministic label-key restoration during reconstruction:
  - Restore `\label{...}` commands from source by occurrence order.
  - Prevent subtle label-key drift (e.g., `-` mutated to `_`) from causing mass `??` cross-reference failures.
- Add deterministic document-tail recovery:
  - Restore tail from source bibliography/appendix anchor when translated output loses `\end{document}`.
  - Fallback by appending missing braces and `\end{document}` if no safe anchor exists.
- Correct inline-math restoration matching:
  - Prevent inline `$...$` restoration logic from mis-parsing `$$...$$` display math delimiters.
- Return structured compilation results through Generator -> Coordinator -> API:
  - `status`, `pdf_path`, `error_summary`, and `warnings`.
  - Emit `compilation_failed` task log events with actionable error summaries.
- Harden compiled PDF path reliability:
  - Remove stale pre-copied `<main>.pdf` before each engine attempt.
  - Normalize compiler output directory paths to absolute paths before invoking `latexmk`/engine commands.
  - Preserve per-engine PDF snapshots during multi-engine fallback to avoid later-engine clobber.
  - Treat non-existent returned `pdf_path` as `failed_compilation` instead of bubbling `[Errno 2]`.
- Add compiler "no PDF fallback error" safeguard:
  - If compilation exits with `error_count=0` but no PDF exists, synthesize a fallback compile error and mark the attempt as failed.
- Update task status mapping:
  - Compilation failure MUST become `failed_compilation`.
  - Human-readable task `message` MUST include real compile error summary.
- Tighten translated PDF resolution:
  - Prefer `task_log.json` `compilation_completed*` events.
  - Use strict convention fallback only.
  - Avoid deep recursive PDF fallback that can hit copied source PDFs.
- Extend terminal-state propagation to API streaming and frontend polling/UI:
  - Treat `failed_compilation` as terminal.
  - Stop polling and show explicit failure UI state.
- Implement Graduated API Rate Limit (429) Resilience:
  - Use infinite retry with progressive backoff (≤3 quick, 4-9 progressive, >9 infinite).
  - Release global LLM concurrency slots (semaphore) during 429 sleep.
  - Fix task manager progress callback deadlocks.
  - Provide amber-pulse UI feedback for rate-limited tasks.
- Implement Automatic PDF Page Dimension and Overflow Protection:
  - Detect and replace `a4wide` with `geometry[a4paper, margin=2cm]` to ensure correct `\textheight` and PDF MediaBox for CJK.
  - Automatically inject `\raggedbottom` for CJK translations to prevent vertical stretching from pushing content past the bottom margin.

## Impact
- Affected specs:
  - `latex-translation-core`
  - `web-api`
  - `web-ui` (UI feedback states)
- Affected code:
  - `backend/app/services/latex/utils.py`
  - `backend/app/services/latex/reconstruct.py`
  - `backend/app/services/agents/generator_agent.py`
  - `backend/app/services/agents/translator_agent.py`
  - `backend/app/services/agents/coordinator_agent.py`
  - `backend/app/services/task_manager.py`
  - `backend/app/api/routes/translate.py`
  - `backend/app/api/routes/download.py`
  - `backend/app/api/routes/task.py`
  - `frontend/src/store/useStore.ts`
  - `frontend/src/pages/Processing.tsx`
  - `frontend/src/components/BatchTranslation.tsx`
- Behavioral outcome:
  - Compilation failures are explicit and visible as `failed_compilation`.
  - Download/preview no longer risks returning copied source PDFs as translated output.
  - API rate limits no longer deadlock the system and provide clear user feedback.
  - Structural translation drift in theorem/definition-like environments no longer causes fatal compile failures from missing wrappers or unsafe header tokens.
  - Malformed display-math shells and out-of-context `\tag` drift no longer silently pass into compilation.
  - Section title command-shell damage and missing title math delimiters are repaired without sacrificing translated wording when safe.
  - `\twopartpiecewise` macro shell drift no longer breaks math-heavy definitions.
  - Truncated translated tails now recover bibliography closure and `\end{document}` deterministically.
  - "No PDF but 0 parsed errors" now reports as explicit compile failure instead of false success.
  - Relative-path compilation invocations no longer generate nested wrong output trees that trigger false `failed_compilation` with `0 errors`.
  - Broken caption wrappers no longer cause `\label without proper reference` and downstream unresolved `\ref` (`??`) artifacts.
  - Cross-reference integrity is preserved by deterministic label restoration, avoiding large-scale unresolved `??` references.

## Why
- Backend-specific structural checks can reject LaTeX that the prototype successfully compiles.
- Backend chunking can isolate immutable placeholder-only fragments and still route them through translation and repair, corrupting downstream reconstruction.
- Generic text environment translation relies on fragile environment-boundary placeholder restoration that can leak synthetic boundary markers into output.
- Section and retry payloads still expose synthetic placeholders directly to the LLM, allowing begin/end placeholder tags to be translated or reordered.
- List environments that contain nested equations or cases can accept translations whose inner environment restoration already failed, leaving residual synthetic tokens in the assembled project.
- Section splitting can leave cross-chunk structure shells (`\begin{...}`, `\end{...}`, `\newpage`) attached to prose, which currently trips payload invariants and falls back to raw English source text.
- Successful compile runs can still leave `structural_fallback_pending_compile` segments stranded because post-compile fallback routing only runs on compile failure.
- Existing validation misses locally catastrophic long English prose spans when aggregate retention metrics still look acceptable.
- Starred section commands such as `\section*{...}` can still be misclassified as malformed during reconstruction, causing translated tail sections to revert back to source English.
- Section-level downgrade can still destroy internal structural tokens embedded inside a translated body (for example placeholders, `\end{...}`, `\newpage`, or `\lettrine`), which can make the regenerated project structurally invalid after post-compile fallback.

## What Changes
- Relax precompile structure guard so macro-body environment tokens produce warnings instead of hard aborts where appropriate.
- Make parser chunking placeholder-aware and mark immutable chunks for passthrough.
- Preserve source environment wrappers for generic text environments and translate only the body.
- Protect synthetic placeholders in section/environment payloads during LLM transport and restore them exactly after response handling.
- Mask residual raw structure tokens (`\begin{...}`, `\end{...}`, lone `$`) before payload invariants run, using the same protected-command transport channel.
- Extract leading/trailing structure shells from section chunks, translate only the core prose, and reattach shells verbatim after translation.
- Fail closed to source content when section or list-environment post-processing still contains synthetic ENV restoration artifacts.
- Short-circuit repair retries for immutable or non-translatable chunks.
- Split payload-invariant passthrough from generic API fallback so invariant-protected sections do not masquerade as no-op retries.
- Add long-English-prose completeness validation and route those failures through targeted retry.
- Run post-compile target-language fallback once whenever compile fallback reports exist, even if the initial compile produced a PDF.
- Add an audit script and regression tests for targeted parity cases.
- Accept starred sectioning commands during reconstruction so translated `\section*{...}` / `\subsection*{...}` blocks are preserved instead of reverted to source text.
- Preserve internal structure tokens inside section fallback bodies while still downgrading the surrounding natural-language prose, so post-compile fallback cannot silently unbalance environment stacks.

## Impact
- Backend should no longer fail known valid prototype outputs before compile.
- Backend should stop sending placeholder-only chunks to the LLM.
- Backend should stop emitting translated placeholder names or residual `ENV_BEGIN`/`ENV_END` markers into reconstructed `.tex` files.
- Failure classification becomes more accurate by separating guard warnings from true compile failures.
- Backend should stop preserving large English prose blocks in papers that the prototype fully translates.
- Audit output should explicitly show invariant-triggered passthrough, structure-shell sections, long-English spans, and pending compile-fallback leftovers.
- Backend should preserve translated tail matter written with starred section commands instead of reverting it to English.
- Post-compile section fallback should no longer corrupt embedded placeholders or environment-boundary tokens and trigger `structure_invalid` regressions.

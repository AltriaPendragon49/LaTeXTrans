# Design: Fix LaTeX Compilation Resilience and Status Propagation

## Context
A failing task sample (`1690e854-7f5d-46ea-b375-fb8d5cf1094e`) showed three connected problems:
- The translated `.tex` replaced many source `\[...\]` blocks with `$$...$$`.
- Some of those blocks wrapped `split` environments, producing fatal LaTeX errors (`Missing } inserted`).
- Upstream orchestration did not propagate compilation failure as a dedicated terminal status, and users received a misleading fallback message.
- Download/preview logic had historical fallback behavior that could risk selecting copied source PDFs instead of the translated PDF.
- In relative-path invocation mode, compiler `-outdir` was passed as a relative path while `cwd` was switched to the TeX directory, which produced nested wrong output trees and false `failed_compilation` results with `0` parsed errors.
- Additional captured math-paper regressions showed structural drift beyond delimiter replacement:
  - malformed display-math shells and `\tag` moving outside display contexts;
  - sectioning command argument corruption with unsafe `_`/`^` title tokens;
  - dropped/broken `\twopartpiecewise` macro calls;
  - translated output truncated before `\end{document}`.

## Goals
- Preserve source display-math delimiter semantics during reconstruction.
- Propagate compilation outcomes as structured data from Generator to API layer.
- Ensure user-facing terminal status accurately reflects compilation failure (`failed_compilation`).
- Make translated PDF resolution deterministic and safe.
- Keep frontend and SSE/polling terminal-state behavior aligned.
- Ensure correct physical page dimensions and overflow prevention for CJK translations.

## Non-Goals
- Rewriting translator prompt strategy.
- Changing database schema.
- Building a full LaTeX semantic fixer beyond delimiter restoration.

## Decisions

### 1. Deterministic delimiter restoration in reconstruction
- Add `restore_display_math_delimiters(original, translated)`.
- Apply only when the source contains `\[`/`\]` and the translated text is missing them.
- Convert unescaped `$$` in ordered pairs into `\[` and `\]`.
- Integrate in `_merge_sections`, `_revert_envs`, and `_revert_captions`.

Rationale:
- This is the narrowest fix that directly addresses the observed failure mode.
- It avoids over-correcting content that did not originally use bracketed display math.

### 2. Structured compilation result contract
- `GeneratorAgent.execute()` returns a structured object instead of bare PDF path:
  - `status`, `pdf_path`, `error_summary`, `warnings`, `engine`, `error_count`.
- `CoordinatorAgent.workflow_latextrans_async()` returns structured status and writes `compilation_failed` events with summary.

Rationale:
- Avoids ambiguous `None` handling and enables precise status mapping.

### 3. Status semantics and message fidelity
- In `translate.run_translation`, map compilation failure to `TaskStatus.FAILED_COMPILATION`.
- Set task `message` and `error` using real error summary instead of static "No PDF found" wording.

Rationale:
- User and frontend should see actionable failure causes.

### 4. Safe translated PDF resolution
- In `download._find_translated_pdf`:
  - First parse `task_log.json` (root and direct child logs) for `compilation_completed*` `pdf_path`.
  - Then use strict naming/convention fallback.
  - Do not recurse into deep source-tree PDFs.

Rationale:
- Prevents source PDF false positives while preserving compatibility for historical output layout.

### 5. Terminal-state propagation consistency
- SSE (`task.py`) treats `completed_with_warnings` and `failed_compilation` as terminal.
- Frontend polling and processing UI stop correctly on `failed_compilation` and present failure state.

Rationale:
- Prevents infinite processing UX on compile-stage failures.

### 6. Graduated API Rate Limit Resilience and Deadlock Prevention
- Implement graduated retry for 429 errors:
  - Hits 1-3: Use `Retry-After` or 10s (max 30s).
  - Hits 4-9: Progressive backoff 35s-60s.
  - Hits >9: Infinite wait (60s) with amber warnings.
- Semantic change: **ALWAYS** release `global_llm_semaphore` during sleep to prevent concurrency deadlock.
- Task Manager Fix: Fix re-entrant lock deadlock in `create_progress_callback` by reading state under lock and updating task state outside.
- UI Feedback:
  - Use `percentage=-1` to signal "message-only update" without resetting progress bar.
  - Use CSS pulse animations and amber colors to indicate rate-limit wait states.

Rationale:
- Infinite wait ensures no partial translation is returned solely due to API limits.
- Semaphore release ensures one project's rate limit doesn't block other projects.
- Explicit UI feedback prevents user confusion during legitimate long waits.

### 7. PDF Page Dimension and Overflow Prevention for CJK
- Implement `_fix_page_overflow_for_cjk(latex_code)` in `utils.py`.
- **Replacement logic**: Detect `a4wide` (standalone or combo `\usepackage{bbm, a4wide}`) and replace/split it to use `geometry[a4paper, margin=2cm]`.
- **Pagination injection**: Inject `\raggedbottom` before `\begin{document}` for all CJK languages (zh, ja, ko).

Rationale:
- CJK fonts have taller metrics than Latin fonts. `a4wide` sets a `\textheight` based on Latin metrics, which causes CJK content to exceed the physical page.
- Using `geometry[a4paper]` forces both the text layout and the PDF driver (xdvipdfmx) to use consistent A4 dimensions.
- `\raggedbottom` prevents LaTeX from expanding vertical glue to fill the page, which can push content off the bottom on crowded pages.

### 8. Deterministic Environment Wrapper + Header Math Repair
- Implement `restore_environment_structure(original, translated)` in `utils.py`.
- Integrate in reconstruction path (`LatexConstructor._revert_envs`) after display-math restoration.
- Repair rules:
  - If source is an environment block and translated block loses `\begin{env}` or `\end{env}`, rebuild wrapper shell with source-compatible begin/end commands.
  - Preserve translated body text whenever possible; fallback to source body only when translated body is empty.
  - If source environment header contains inline math but translated header drops delimiters and leaves unsafe `_`/`^`, first repair translated header by wrapping math-like tokens (e.g., `Y_i` -> `$Y_i$`).
  - Only fallback begin header to source command if translated header remains unsafe after repair.
  - If translated body is fully wrapped by an unsafe non-ASCII inner environment command, strip that inner wrapper and keep translated body content.

Rationale:
- Type-C command mismatch retries are not sufficient for wrapper loss (e.g., theorem shell translated into plain text).
- Reconstruction has both source+translated fragments and is the most deterministic place to enforce compile-safe structure.
- Header-level math loss in optional titles (e.g., `Y_i`) is a common fatal error and can be repaired while preserving translated (Chinese) wording in most cases.
- Non-ASCII translated environment names can trigger fatal `\csname...\endcsname` errors and must be normalized without discarding translated prose.

### 9. Deterministic Label-Key Restoration
- Implement `restore_label_commands(original, translated)` in `utils.py`.
- Integrate in reconstruction for sections/envs/captions before final write.
- Repair rules:
  - Replace translated `\label{...}` commands with source label commands by positional order.
  - If translated text drops labels entirely, append missing source labels as a safe fallback.

Rationale:
- A single label-key mutation can break dozens of `\ref` resolutions and produce many `??`.
- Label commands are structural anchors, so deterministic restoration is safer than LLM retries.

### 10. Compiled PDF Path Integrity Guard
- In compiler engine attempts, remove stale expected `<basename>.pdf` before each run to avoid treating copied source PDFs as compiled outputs.
- During multi-engine fallback, preserve each engine's produced PDF into `<basename>.<engine>.pdf` snapshot before trying the next engine.
- In coordinator and API mapping, treat returned-but-missing `pdf_path` as compilation failure (`failed_compilation`) with actionable summary.

Rationale:
- A later failed engine can delete or overwrite the shared `<basename>.pdf`, leaving stale in-memory paths.
- Without existence guard, the pipeline may raise `[Errno 2]` while moving a non-existent PDF, masking the real compilation issue.

### 11. Absolute Output-Directory Normalization for Engine Calls
- Resolve `tex_file` and `output_dir` to absolute paths before invoking `latexmk` or direct engine commands.
- Pass absolute `-outdir` / `-output-directory` values to engine commands.
- Evaluate expected `pdf_path` and `log_path` against the same normalized absolute output directory.

Rationale:
- Eliminates `cwd`-relative path drift that can silently write outputs into nested unintended directories.
- Prevents false negatives where compilation succeeds but the checker looks at a different path and reports `failed_compilation`.

### 12. Caption Command-Structure Safety Net
- Add deterministic caption-shell repair for caption fragments:
  - Validate command sequence/count for `\caption`, `\subcaption`, `\captionof`.
  - Validate command argument structure (including optional `[...]` and required `{...}` groups).
  - Fallback to source caption fragment when translated command structure is missing or malformed.
- Keep translated caption content when structure is valid.

Rationale:
- Caption wrapper loss (e.g., plain text replacing `\caption{...}`) leaves `\label` outside caption context and triggers unresolved references (`??`) despite successful PDF generation.
- Fragment-level fallback keeps impact minimal and preserves Chinese where structurally safe.

### 13. Display-Math Shell Structural Guard
- Add `restore_display_math_shell_structure(original, translated)` in reconstruction flow after delimiter repair.
- Detect malformed shell states:
  - unbalanced/odd `$$`;
  - cross-shell mixing drift between `\[`/`\]` and `$$...$$`.
- Apply strict fallback to source fragment only when source shell is structurally valid and translated shell is malformed.

Rationale:
- Delimiter normalization alone cannot recover shell-level corruption in heavily edited formula fragments.
- Fragment-level guard avoids global rollback while removing a common hard-failure source in math papers.

### 14. \tag Context Safety Enforcement
- Extend `restore_tag_commands` with context validation:
  - detect `\tag{...}` tokens outside display-math contexts (`\[...\]`, `$$...$$`, display math environments).
  - fallback the fragment when translated `\tag` escapes display context and source context is valid.
- Preserve existing deterministic replacement/removal behavior for tag count drift.

Rationale:
- `\tag` outside display math can trigger fatal parsing or numbering errors and is hard to recover downstream.
- Context-aware fallback keeps repair precise and deterministic.

### 15. Sectioning Command Shell + Title Math Repair
- Add `restore_sectioning_command_structure(original, translated)` before other section-level structural repairs.
- Validate sectioning command sequence and balanced argument groups.
- For translated titles that dropped inline math delimiters while keeping unsafe `_`/`^` tokens:
  - first attempt local token wrapping (`Y_i` -> `$Y_i$`) to preserve translated wording;
  - fallback to source section command only if repaired title remains unsafe.

Rationale:
- Heading-shell corruption is a high-frequency LLM drift in math text and can break compilation early.
- Translation-preserving local repair minimizes unnecessary source-language fallback.

### 16. twopartpiecewise Macro Shell Restoration
- Add `restore_twopartpiecewise_commands(original, translated)` in section/env/caption reconstruction paths.
- Restore source `\twopartpiecewise{...}{...}{...}{...}` calls by occurrence order.
- Fallback to source fragment when translated command count mismatches or command is dropped.

Rationale:
- This macro is brace- and argument-sensitive; minor translation drift makes it uncompilable.
- Deterministic source-shell restoration is safer than LLM retries for this command family.

### 17. Document Tail Completion Safety Net
- Add `restore_document_tail_structure(original_main_tex, reconstructed_tex)` before language-package injection and file write.
- If translated output drops `\end{document}`, recover tail from source using late anchors (`\bibliography`, `thebibliography`, `\appendix`).
- If no reliable anchor is available, append missing closing braces and `\end{document}` as fallback.

Rationale:
- Tail truncation appears in long math documents and causes non-local compilation failure.
- Anchor-first recovery preserves maximal translated content while guaranteeing document closure.

### 18. No-PDF/Zero-Error Fallback Normalization in Compiler
- In both `latexmk` and direct-engine paths:
  - if `pdf_exists == False` and parsed `error_count == 0`, synthesize a fallback compile error with exit code context;
  - set `success=False`.

Rationale:
- Some failing runs produce no parseable log error despite no PDF output; treating those as success masks real failures.
- Fallback normalization ensures status propagation remains truthful.

## Risks and Trade-offs
- Conservative delimiter restoration may leave some malformed math untouched when mapping is ambiguous.
- Structured status propagation changes internal interfaces; callers must be updated together.
- Strict PDF resolution may expose older malformed outputs that previously worked by permissive fallback.
- For some repaired environments, header text may fallback to source language to preserve compile safety.
- Positional label restoration assumes source/translated label ordering remains aligned within each fragment.
- Section-title math wrapping may over-wrap rare non-math tokens that syntactically resemble math identifiers.
- Tail fallback brace completion may not preserve exact semantic intent in severely truncated outputs.

## Migration Plan
1. Deploy backend changes together (generator/coordinator/translate/download/task).
2. Deploy frontend status handling in same release window.
3. Monitor `task_log.json` events for `compilation_failed` volume and error-summary quality.
4. If needed, add targeted formatter for additional delimiter variants in a follow-up change.
5. Keep captured-config replay checks for the four math-paper snapshots as a release gate.

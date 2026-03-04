# Tasks: fix-latex-compilation-resilience

## 1. Root Cause Fix (Display Math Delimiters)
- [x] 1.1 Add `restore_display_math_delimiters(original, translated)` in `backend/app/services/latex/utils.py`.
- [x] 1.2 Apply delimiter restoration in `LatexConstructor._merge_sections`.
- [x] 1.3 Apply delimiter restoration in `LatexConstructor._revert_envs`.
- [x] 1.4 Apply delimiter restoration in `LatexConstructor._revert_captions`.

## 2. Structured Compilation Failure Propagation
- [x] 2.1 Change `GeneratorAgent.execute()` to return structured result (`status`, `pdf_path`, `error_summary`, `warnings`, `engine`, `error_count`).
- [x] 2.2 Change `CoordinatorAgent.workflow_latextrans_async()` to return structured workflow result and emit `compilation_failed` task log event.
- [x] 2.3 Update `translate.run_translation` to map compile failure to `TaskStatus.FAILED_COMPILATION`.
- [x] 2.4 Ensure task `message`/`error` use real compile summary instead of generic missing-PDF text.

## 3. Translated PDF Resolution Safety
- [x] 3.1 Rewrite `_find_translated_pdf` to prioritize `task_log.json` `compilation_completed*` `pdf_path`.
- [x] 3.2 Keep strict fallback by naming convention only.
- [x] 3.3 Prevent deep recursive fallback from selecting copied source PDFs.

## 4. Terminal-State Linkage (Backend + Frontend)
- [x] 4.1 Extend SSE terminal states in `backend/app/api/routes/task.py`.
- [x] 4.2 Extend polling terminal states in `frontend/src/store/useStore.ts`.
- [x] 4.3 Update processing page failure rendering for `failed_compilation`.

## 5. Tests and Validation
- [x] 5.1 Add unit tests for display math delimiter restoration.
- [x] 5.2 Add unit tests for translated PDF resolver behavior (including nested source PDF false-positive prevention).
- [x] 5.3 Add flow tests for translation status mapping (`completed_with_warnings` and `failed_compilation`).
- [x] 5.4 Add SSE terminal-state tests for `failed_compilation` and `completed_with_warnings`.
- [x] 5.5 Run targeted backend tests and frontend build verification.
- [x] 5.6 Update OpenSpec proposal/design/tasks/spec deltas and run strict validation.

## 6. API Rate Limit Resilience (429 Handling)
- [x] 6.1 Implement graduated backoff logic in `TranslatorAgent._request_llm_for_*` methods.
- [x] 6.2 Ensure `asyncio.sleep` for 429 occurs outside the `global_llm_semaphore` context.
- [x] 6.3 Implement `-1` percentage logic in `TaskManager.create_progress_callback` to support message-only updates.
- [x] 6.4 Handle re-entrant task management lock deadlock.
- [x] 6.5 Implement Automatic PDF Page Dimension fix (geometry/raggedbottom).
- [x] 6.6 Update `BatchTranslation.tsx` task list with amber-pulse styling for rate-limited tasks.
- [x] 6.7 Update `Processing.tsx` with rate-limit warning banner.
- [x] 6.8 Verify 429 concurrency by simulating multiple project translations.
- [x] 6.9 Test status propagation end-to-end.

## 7. Environment Structural Repair for Compilation Safety
- [x] 7.1 Add `restore_environment_structure(original, translated)` in `backend/app/services/latex/utils.py`.
- [x] 7.2 Apply environment structural repair in `LatexConstructor._revert_envs`.
- [x] 7.3 Add unit tests for missing wrapper restoration and unsafe header math repair (Chinese-preserving first, source fallback second).
- [x] 7.5 Add unit test and repair rule for stripping unsafe translated inner wrappers (e.g., non-ASCII `\begin{...}`) while preserving translated body.
- [x] 7.4 Validate against captured failing outputs:
  - `c63345dd-ffcf-4233-ac2b-2ecff337e5b2`
  - `6d3450f9-68f1-47bd-ad93-ad779982a662`

## 8. Cross-Reference Integrity (Label Key Restoration)
- [x] 8.1 Add `restore_label_commands(original, translated)` in `backend/app/services/latex/utils.py`.
- [x] 8.2 Apply label restoration in reconstruction paths for sections/envs/captions.
- [x] 8.3 Add unit tests for mutated label-key recovery and dropped-label fallback.
- [x] 8.4 Validate `c633.../main.tex` cross-reference warning regression:
  - Recover `\label{cor:leave-out-rank-and-max-spacing}` from mutated form.
  - Re-run compile and verify undefined reference warnings are cleared under sequential compile verification.

## 9. Compiled PDF Path Integrity Guards
- [x] 9.1 Remove stale expected `<basename>.pdf` before each engine attempt in compiler paths.
- [x] 9.2 Preserve engine-specific PDF snapshots during fallback (`<basename>.<engine>.pdf`) before trying next engine.
- [x] 9.3 Add coordinator/API existence checks so missing returned `pdf_path` maps to `failed_compilation` instead of `[Errno 2]`.
- [x] 9.4 Add regression tests for missing/non-existent PDF path handling.

## 10. Relative Path + Caption Wrapper Regressions
- [x] 10.1 Normalize compiler `tex_file`/`output_dir` to absolute paths before invoking `latexmk` or direct engines.
- [x] 10.2 Add regression test for relative `output_dir` invocation to prevent nested wrong output trees and false `failed_compilation`.
- [x] 10.3 Add `restore_caption_command_structure` safety net for caption fragments in reconstruction.
- [x] 10.4 Apply caption command-structure repair in `LatexConstructor._revert_captions`.
- [x] 10.5 Add unit tests for caption command mismatch/malformed fallback and valid translated caption pass-through.
- [x] 10.6 Validate captured failing task `3b428d22-fbfd-4323-959c-ccc26e285db8`:
  - Reconstruct + compile in output directory succeeds (`status=completed`).
  - Undefined reference warnings in `main.log` reduced to zero (`undef_refs=0`).

## 11. Math Snapshot Structural Hardening (2026-02-25)
- [x] 11.1 Add `restore_display_math_shell_structure(original, translated)` and apply in sections/envs/captions reconstruction flow.
- [x] 11.2 Extend `restore_tag_commands` with display-math context validation and source fallback when `\tag` escapes display context.
- [x] 11.3 Add `restore_sectioning_command_structure(original, translated)` to repair section command-shell drift and unsafe title math tokens.
- [x] 11.4 Add `restore_twopartpiecewise_commands(original, translated)` and apply in sections/envs/captions reconstruction flow.
- [x] 11.5 Add `restore_document_tail_structure(original, translated)` before writing reconstructed main tex output.
- [x] 11.6 Tighten `restore_inline_math_segments` matching so inline repair never corrupts `$$...$$` display math.
- [x] 11.7 Add compiler fallback error normalization for `pdf_missing && error_count==0` in both `latexmk` and direct-engine paths.
- [x] 11.8 Add/refresh regression tests:
  - `test_restore_display_math_shell_structure.py`
  - `test_restore_document_tail_structure.py`
  - `test_restore_twopartpiecewise_commands.py`
  - `test_restore_sectioning_command_structure.py`
  - `test_restore_tag_commands.py`
  - `test_restore_inline_math_segments.py`
  - `test_compiler_no_pdf_error_fallback.py`
- [x] 11.9 Validate four-paper end-to-end completion after fixes:
  - `80f688b3-fc15-4f3d-8a70-2913397dc6e7` (`compilation_completed`)
  - `ede0e912-2890-4fdd-a8ae-78bd5b2035a5` (`compilation_completed`)
  - `82e683f9-700e-4659-adf5-ec5b4d9ca154` (`compilation_completed`)
  - `28ff3d3c-3f14-43d2-82fc-4c6e93aee1cb` (`compilation_completed`)

## 12. Sensitive Command Pre-Translation Protection (Emergency Regex Masking)
- [x] 12.1 Create `PROTECTED_COMMANDS` registry in `backend/app/services/latex/utils.py` with initial entries (`\ccsdesc`, `CCSXML` environment, `\received`, `\keywords` for ACM templates).
- [x] 12.2 Implement `mask_sensitive_commands(content, registry)` → returns `(masked_content, mapping_dict)`.
- [x] 12.3 Implement `unmask_sensitive_commands(translated_content, mapping_dict)` → returns restored content.
- [x] 12.4 Integrate masking in `TranslatorAgent._request_llm_for_trans` before sending to LLM, and unmasking on result. Also integrated in `_request_llm_for_trans_with_terms`.
- [x] 12.5 Add structured JSON logging of all masked commands per task to `data/protection_log/`.
- [x] 12.6 Add unit tests for mask/unmask round-trip, including edge cases (nested braces, multi-line environments).

## 13. Target Language Persistence & Retranslation Hardening
- [x] 13.1 Update `restore_display_math_shell_structure` to keep translated text instead of nuclear fallback to English.
- [x] 13.2 Update `restore_tag_commands` to append missing tags instead of falling back to English.
- [x] 13.3 Update `restore_twopartpiecewise_commands` to handle mismatches by replacing/appending commands while keeping translated text.
- [x] 13.4 Apply `mask_sensitive_commands` to the combined `[Original]/[Translation]/[Error]` prompt string in `_request_llm_for_retrans_error_parts`.
- [x] 13.5 Update relevant unit tests (`test_restore_display_math_shell_structure`, `test_restore_tag_commands`, `test_restore_twopartpiecewise_commands`) to expect the new behavior.

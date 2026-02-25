# Tasks for Incorporate User Feedback Optimizations

## 1. Update Website Branding and Metadata
- [x] Update `<title>` tag in `index.html` (or equivalent main template).
- [x] Obtain or generate a `favicon.ico` file.
- [x] Add the `<link rel="icon" ...>` tag linking to the favicon in the main HTML file.

## 2. Robust Guest Task Cleanup
- [x] Implement `collect_orphaned_tasks()` in `main.py` (or `task_manager.py`) to scan `data/outputs` and `data/terms`. 
- [x] Determine tasks older than `settings.guest_task_ttl_hours` (using directory modification time).
- [x] Query the Supabase `translation_tasks` table in a single bulk request to see which of the old directory names exist in the DB.
- [x] Enhance the `periodic_cleanup` background loop in `main.py` to delete directories not found in the DB.
- [x] Add robust error handling to prevent accidental deletion if Supabase is down or unreachable.

## 3. Email Notification Implementation
- [x] Update frontend `AdvancedConfig` UI (e.g. in `TranslationConfig.tsx`) with a switch for `发送邮件通知 (完成时)` and payload bindings.
- [x] Create `EmailService` in `backend/app/services/email_service.py` to send HTML emails using Python's `email` and `smtplib` modules.
- [x] Add SMTP credentials (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`) to `core/config.py` and `.env.example`.
- [x] Update task state transitions (in `task_manager.py` or `task_queue.py`) to trigger `EmailService.send_task_completed_email()` when a task requests it and successfully finishes.

## 4. ArXiv Download Optimization & Progress UI
- [x] Edit `backend/app/services/latex/utils.py` to add a throttle `last_reported_progress` variable to `DownloadProgressCallback`.
- [x] Create a `shimmer` keyframe animation in `frontend/src/index.css`.
- [x] Update `frontend/src/components/ui/progress.tsx` with smoother transitions.
- [x] Overhaul the download progress section in `frontend/src/pages/Dashboard.tsx` to include the shimmer bar, textual stage descriptors, and pinging dot.

## 5. Typography Parameter Bounds Validation
- [x] Backend: Add validation in `utils.py:apply_formatting_config` to reject font sizes outside `[8, 14]` and line spacing outside `[1.0, 2.5]`.
- [x] Backend: Skip injection and append explanatory warning messages to `fmt_warnings`.
- [x] Frontend: Update `FormattingPanel.tsx` `NumericField` props with corresponding `min`, `max`, and explanatory tooltips.
- [x] Tests: Update `test_apply_formatting_config.py` to verify out-of-bounds inputs are skipped safely.

## 6. CJK Font Compatibility Fix
- [x] Add patterns for `fontenc[T1]`, `newtxtext`, `newtxmath`, `txfonts`, and `\pdfinclusioncopyfonts` to `_comment_out_pdflatex_commands`.
- [x] Implement `_patch_sibling_style_files` to dynamically scan and neutralize pdfLaTeX-only font packages in local `.cls` and `.sty` files prior to XeLaTeX compilation.
- [x] Update `reconstruct.py` and `add_cjk_package`/`add_ctex_package` to pass the `tex_file_path` downward for the style patching function.

## 7. Translation Intra-Section Parallelization
- [x] Refactor `TranslatorAgent.translate()` to use `asyncio.gather()` for environment translation: collect all matching envs, fire concurrent `_translate_env()` calls, write results back.
- [x] Refactor `TranslatorAgent.translate()` to use `asyncio.gather()` for caption translation: collect all captions (including those discovered from env content), fire concurrent `_translate_caption()` calls, write results back.
- [x] Ensure the 3-phase ordering (body → envs → captions) is preserved so that captions inside envs are not missed.
- [x] Add unit test `test_translator_intra_section_parallel.py` to verify that envs and captions are translated concurrently (mock LLM, assert gather behavior and result correctness).
- [x] Validate with a real translation run and compare total time against before (manual verification).

## 8. Global API Rate Limiting
- [x] Add `LLM_MAX_CONCURRENT_REQUESTS` (default: 30) to `core/config.py` and `.env.example`.
- [x] Instantiate a global `asyncio.Semaphore(settings.llm_max_concurrent_requests)` in a central location (`services/agents/__init__.py`).
- [x] Update `TranslatorAgent._request_llm_for_trans` (and related LLM request methods) to `async with global_llm_semaphore:` before executing `session.post`.
- [x] Ensure the global semaphore correctly queues excess requests across multiple concurrent tasks without blocking the main event loop.

## 9. LLM Timeout & Retry Robustness
- [x] Fix incorrect exception type (`requests.exceptions.RequestException` -> `aiohttp.ClientError, asyncio.TimeoutError`) in `_request_llm_for_retrans_error_parts`.
- [x] Increase `timeout` to 180 seconds in all `TranslatorAgent` LLM methods.
- [x] Replace fixed 5s sleep with exponential backoff (5s, 10s, 20s) for retries.
- [x] Implement HTTP 429 detection and `Retry-After` header parsing to explicitly throttle requests when rate-limited.

## 10. Legacy Verification Config Cleanup
- [x] Remove `enable_verification` from `compute_config_hash` definition and calls.
- [x] Remove `enable_verification` from `translate.py` logging statements.
- [x] Hardcode `use_verification_agent: False` in `translate.py` agent configuration.

## 11. Biblatex Undefined References Fix
- [x] Implement `_fallback_biblatex_to_thebibliography` in `compiler.py` to extract core bibliographic data (author, title, year) directly from incompatible `biblatex` v3.2 `.bbl` files using a custom Python brace-matching parser.
- [x] Automatically comment out `\usepackage{biblatex}` and replace `\printbibliography` with a generated `\begin{thebibliography}` native block when compiling arXiv projects missing `.bib` files, completely removing the `biblatex` rendering dependency to resolve "Undefined control sequence" and garbled text leakage.

## 12. Translation Completeness Validation
- [x] (FAILED - PENDING CORRECTION) Prompts: Add explicit rules mandating the translation of all text (including `\item` lists) to all 10 prompt variants in `backend/app/services/latex/prompts.py`.
- [x] Validator: Introduce `ERROR_TYPE_T` and implement `_validate_translation_completeness` in `backend/app/services/agents/validator_agent.py` to algorithmically calculate the English prose retention ratio.
## 13. LaTeX Bracket Validation Accuracy
- [x] Modify `_find_brackets_errors` in `backend/app/services/agents/validator_agent.py`.
- [x] Remove mapping for `(): ()` logic to prevent false positives when validating lists.

## 14. Translation Output Persistence
- [x] Create a `_find_translated_pdf` helper in `backend/app/api/routes/download.py` that prioritizes files ending with `_translated.pdf` in the base output directory and explicitly ignores recursive descent into heuristic source directories (like `2503.19300/`).
- [x] Update `download_pdf` and `preview_pdf` routes to rely on the new helper.
- [x] Add a `_write_task_log` method to `CoordinatorAgent` (`backend/app/services/agents/coordinator_agent.py`) leveraging the `json` module.
- [x] Call `_write_task_log` at logical state transitions: task start, parsing complete, translation complete, compilation complete (with/without warnings), and error traps.

## 15. Prompt Concurrency Isolation
- [x] Add module-level `threading.Lock()` and a `create_prompts(source_lang, target_lang) -> dict` method to `backend/app/services/latex/prompts.py`.
- [x] Update `TranslatorAgent.execute()` and `ParserAgent.execute()` to utilize the thread-safe `create_prompts` via `self.prompts`.
- [x] Exhaustively replace all occurrences of `pm.[name]_prompt` across both agents with the isolated dictionary counterpart `self.prompts['[name]_prompt']`.

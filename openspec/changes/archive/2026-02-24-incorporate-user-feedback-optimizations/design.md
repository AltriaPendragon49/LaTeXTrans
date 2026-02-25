# Design for User Feedback Optimizations

## Robust Guest Task Cleanup
The current `GuestTaskTracker` is an in-memory dictionary. If the backend restarts, it forgets all guest tasks created prior to the restart, leading to permanently orphaned folders in `data/outputs/` and `data/terms/`.

**Chosen Solution:**
Enhance the existing `periodic_cleanup` looping task in `main.py` to be state-independent:
1. Iterate over all directories in `outputs_dir` and `terms_dir`.
2. Filter directories whose modification/creation time is older than the `guest_task_ttl_hours` (e.g., 2 hours).
3. Extract the `task_id` (which is the directory name).
4. Query the Supabase `translation_tasks` table to check if these `task_id`s exist.
5. If a `task_id` does not exist in the database, it is either an expired guest task or an orphaned folder from a manually deleted authenticated task. It can be safely removed using `shutil.rmtree`.
*Why this is better:* This approach requires no changes to how files are stored (avoiding complex path management like `output/temp/`), prevents any storage leaks globally, and acts as a bulletproof garbage collector for both guest users and deleted authenticated tasks.

## Email Notification on Task Completion
Users translating large PhD theses or batch jobs need to know when their translations finish without keeping the page open.

**Chosen Solution:**
- **Frontend Configuration:** Add a toggle switch `发送邮件通知 (完成时)` in the Advanced Configuration panel (`TranslationConfig.tsx`). This adds an `email_notification` boolean to the `advanced_config` payload.
- **Backend Delivery Mechanism:** Supabase's built-in email service is restricted to Auth events (Magic Link, OTP) and cannot easily send arbitrary application emails without Edge Functions. Since the translation backend is already managing the task lifecycle and state transitions, the simplest and most robust approach is to configure standard SMTP directly in the Python backend.
- **Implementation:** Introduce an `EmailService` in `backend/app/services/email_service.py` initialized via `.env` variables (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`). When `TaskManager` or `TaskQueue` transitions a task (that requested notification) to `COMPLETED` or `FAILED`, it will trigger this service to dispatch a notification email.

## ArXiv Download Optimization & Progress UI
**The Problem:** The existing system was excessively updating Supabase. Because `requests.get.iter_content` fetches data in 8KB chunks, the `DownloadProgressCallback` was invoking `task_manager.update_task` thousands of times during a single download, creating an immense database I/O bottleneck that severely throttled download speeds. Furthermore, the frontend progress bar remained basic and unpolished.

**Chosen Solution:**
- **Backend Throttling:** Introduce an integer instance variable `last_reported_progress` string in the callback. A database write will now only trigger if the integer percentage changes (or if the stream completes). This curtails writes from thousands down to an absolute maximum of 100 per stage (usually ~30-40 actual writes due to network bursts).
- **Frontend Refinement:** Upgrade the download progress UI. Adhere to `ui-ux-pro-max` guidelines by replacing the basic component with a styled backdrop pane that includes an animated shimmer (`@keyframes shimmer`), pulsing active state dots, explicit localization labels for `downloading`, `extracting`, `downloading_pdf`, and `validating`, along with smooth 300ms transitions on the actual progress indicator.

## Typography Parameter Bounds Validation
**The Problem:** Users were capable of entering extreme values for font size (e.g., 50pt) and line spacing (e.g., 5.0), leading to broken LaTeX compilations or visually disproportionate PDFs.

**Chosen Solution:**
- **Backend Enforcement:** Add explicit boundary checks in `apply_formatting_config` (`backend/app/services/latex/utils.py`). For font sizes `< 8` or `> 14` pt, and line spacing `< 1.0` or `> 2.5`, skip the injection entirely and return a warning string in the `fmt_warnings` list to notify the user.
- **Frontend Alignment:** Reflect these identical bounds in the numerical input fields of `FormattingPanel.tsx`, setting `min` and `max` attributes and updating the tooltips to explicitly state these limitations.

## CJK Font Compatibility Fix
**The Problem:** Certain translations (e.g., `2505.02429`) rendered correctly translated Chinese `.tex` content, but the resulting PDF was completely blank or missing all CJK characters. The error logs revealed tens of thousands of `Missing character: There is no X in font nullfont!` warnings. The root cause was custom document classes like `atlasdoc.cls` utilizing `\RequirePackage[T1]{fontenc}` along with `newtxtext`/`newtxmath`, which are pdfLaTeX-specific font packages that fundamentally conflict with XeLaTeX's Unicode-native font handling (via `ctex`/`fontspec`).

**Chosen Solution:**
- Expand the `pdflatex_single_patterns` regex list in `utils.py:_comment_out_pdflatex_commands` to target and comment out `fontenc[T1]`, `newtxtext`, `newtxmath`, `txfonts`, and `\pdfinclusioncopyfonts`.
- Introduce `_patch_sibling_style_files(tex_file_path)`: Since these conflicting font commands reside inside included `.cls` or `.sty` files rather than the main `.tex` file, this new function iterates through sibling style files in the output directory and neutralizes the conflicting lines before XeLaTeX compilation.
- Thread the `tex_file_path` correctly backwards through `reconstruct.py` -> `add_cjk_package` -> `add_ctex_package`.

## Translation Intra-Section Parallelization
**The Problem:** The current `TranslatorAgent.translate()` method already parallelizes across sections using `asyncio.Semaphore(10)`. However, *within* each section's `translate()` call, the child environments and captions are translated **sequentially**: the method awaits `_translate_env()` one by one in a `for` loop, then awaits `_translate_caption()` one by one. This means a section with 1 body + 5 environments + 3 captions makes 9 serial LLM requests. With a typical ~3s latency per request, this single section takes ~27 seconds instead of the ~3s it would take if all requests ran concurrently. For papers with many environments per section, this is the dominant bottleneck.

**Chosen Solution:**
Refactor `TranslatorAgent.translate()` to use `asyncio.gather()` for the environment and caption translation loops:
1. **Phase 1 — Section body:** Translate the section body text (single await, unchanged).
2. **Phase 2 — Environments (concurrent):** Collect all envs referenced by placeholders in the section, fire all `_translate_env()` calls concurrently via `asyncio.gather()`, and write results back.
3. **Phase 3 — Captions (concurrent):** Collect all captions (including those newly discovered from envs in Phase 2), fire all `_translate_caption()` calls concurrently via `asyncio.gather()`, and write results back.

Phase 2 and Phase 3 remain sequential relative to each other because captions inside environments are discovered during Phase 2 (env content contains `<PLACEHOLDER_CAP_X>` references). This ensures no captions are missed.

*Why this is safe:*
- Each `_translate_env`, `_translate_caption`, and `_translate_section` call sends an independent, stateless HTTP request to the LLM API with no shared conversation history. Concurrent execution produces identical results to sequential execution.
- The existing `Semaphore(10)` at the inter-section level already allows 10 sections to translate simultaneously. Adding intra-section concurrency does not change the total concurrency model; it merely removes artificial serialization within each section.
- For `trans_mode=2` (dynamic terminology extraction with `update_term=True`), the `term_dict` is already updated in a race condition across sections. Intra-section parallelization does not worsen this; the existing behavior is non-deterministic in term insertion order regardless.

*Why NOT gather section body + envs + captions all at once:*
Captions embedded inside environments (`<PLACEHOLDER_CAP_X>` inside env content) are discovered by scanning env content. If we translated the section body and all envs and all captions simultaneously, we would need to pre-scan all env content for caption placeholders before starting. While feasible, this adds complexity. The chosen 3-phase approach is simpler and still captures ~80-90% of the speedup since the env and caption loops are the primary serial bottlenecks.

## Global API Rate Limiting
**The Problem:** While intra-section parallelization dramatically speeds up individual tasks, it behaves as a multiplier on API load. Previously, a task generated at most 10 concurrent requests (due to the inter-section semaphore). With intra-section gathering, a single task could burst to 30-50 concurrent requests. Furthermore, multi-user systems running 5 simultaneous translations could blindly throw 200+ concurrent requests at the LLM provider. External APIs (like the NVIDIA NIM free tier, which imposes strict limits like 40 RPM, or OpenAI's tier-based limits) will instantly return `HTTP 429 Too Many Requests`, causing massive failure cascades.

**Chosen Solution:**
Implement a globally shared `asyncio.Semaphore` at the application level (e.g., inside `TaskManager` or a dedicated `RateLimiter` singleton) and pass it down to `TranslatorAgent`. 
- Every outbound `session.post` to the LLM API must acquire this global semaphore.
- The default limit will be configurable via environment variables (e.g., `LLM_MAX_CONCURRENT_REQUESTS=30`), allowing administrators to tailor it to their specific LLM provider's tier (e.g., 30 for small providers, 200 for enterprise/self-hosted Triton NIM instances).

*Why this is safe:*
This cleanly decouples "task logic concurrency" from "network capacity concurrency". `TranslatorAgent` can still attempt to `asyncio.gather()` 100 things at once, but only the globally permitted number of actual HTTP requests will be on the wire simultaneously. The rest will safely yield in the event loop waiting for the global semaphore, completely eliminating `429` explosions without stalling the main application thread.

## LLM Timeout & Retry Robustness
**The Problem:** During batch translation tasks, heavy concurrency led to LLM API rate limiting (HTTP 429) and delayed responses. The `TranslatorAgent` had a rigid 100s timeout and a fixed 5s retry. More critically, the `_request_llm_for_retrans_error_parts` method incorrectly attempted to catch `requests.exceptions.RequestException` for an `aiohttp` asynchronous request, meaning timeouts bypassed the retry logic entirely and crashed the entire translation task.

**Chosen Solution:**
- Fix the exception types in `_request_llm_for_retrans_error_parts` to catch `(aiohttp.ClientError, asyncio.TimeoutError)`.
- Increase the baseline `aiohttp.ClientTimeout` to 180 seconds across all 6 LLM request methods in `TranslatorAgent`.
- Implement exponential backoff (`5 * (2 ** (attempt - 1))`) for general retries to prevent retry avalanches.
- Add specific checks for response status `429`, extract the `Retry-After` header (defaulting to `10 * attempt` seconds), and pause the coroutine, ensuring the system respects provider rate limits smoothly.

## Legacy Verification Config Cleanup
**The Problem:** A previous OpenSpec change removed the `enable_verification` field from the `AdvancedConfig` model, but missed several references in `translate.py` (such as in `compute_config_hash` and logging statements). This caused an `AttributeError` when starting a translation.

**Chosen Solution:**
- Strip all `enable_verification` references from `translate.py`, adjusting `compute_config_hash` to no longer require it, and hardcoding `use_verification_agent=False` during agent configuration.

## Biblatex Undefined References Fix
**The Problem:** When compiling certain translated arXiv papers (e.g., `2501.04040`), the resulting PDF's bibliography section either entirely vanished or rendered 50+ pages of raw `biblatex` `.bbl` source code. This occurred because arXiv submissions often bundle older versions of `.bbl` files (e.g., v3.2) without including the original `.bib` sources. Modern local LaTeX environments running `biblatex` v3.3+ cannot parse these older `.bbl` files, throwing `Undefined control sequence` errors (due to deprecated internal macros like `\hash` or `\name`) and dumping the unparsed structure into the PDF.

**Chosen Solution:**
- **Python `.bbl` Extraction Fallback:** Because the `.bib` source is unavailable and coercing local LaTeX to understand obsolete internal `biblatex` binaries is highly unstable, the ideal solution sidesteps LaTeX completely. 
- **Robust Parsing:** Implemented `_fallback_biblatex_to_thebibliography` in `compiler.py`. This reads the incompatible `.bbl` file, utilizes a stack-based bracket-matching parser (to safely handle nested LaTeX characters in fields like author names, avoiding early truncations), and extracts the `author`, `title`, and `year`.
- **Native Injection:** The compiler then scans `.tex` files, comments out `\usepackage{biblatex}`, and strips out `\printbibliography`. In its place, it injects a completely standard `\begin{thebibliography} ... \end{thebibliography}` block generated from the extracted data. This guarantees zero `biblatex` version conflicts because the dependency is removed entirely.

## Translation Completeness Validation
**The Problem:** During translation of sections with heavy technical lists (e.g., `2406.00515`), the LLM would translate the natural language surrounding the list but completely skip translating the actual English bullet points, treating them as non-translatable technical jargon. 

**Chosen Solution:**
- **Algorithmic Validation:** Introduce a new validation error type (`ERROR_TYPE_T`) and a `_validate_translation_completeness` function in `validator_agent.py`. This strips out LaTeX math/commands and counts English "prose" words, flagging the section if the translation retains >55% of the English source words while producing minimal CJK characters.
- **Automated Retranslation:** Update `translator_agent.py` to catch `ERROR_TYPE_T` and send the section back to the LLM with a highly specific completeness error message ("Translation is incomplete... You MUST translate ALL natural language text...").
- **Failed Prompt Engineering Attempt (Pending Correction):** Initially, strict rules mandating the translation of all list items were appended to all 10 prompt variants in `prompts.py`. However, this approach failed to resolve the issue reliably out-of-the-box and requires future correction. The algorithmic validation acts as the current working safeguard.

## LaTeX Bracket Validation Accuracy
**The Problem:** The regex-based validation for mismatched brackets in `validator_agent.py` was overly aggressive, checking for both `[]`, `{}`, and `()`. This caused legitimate mathematical lists in `.tex` files (e.g., `1)`, `2)`) to be falsely flagged as B-type errors if the LLM dropped the source entirely or formatted it slightly differently.

**Chosen Solution:**
- Remove the mapping for `(): ()` in `_find_brackets_errors` within `validator_agent.py`.
- Limit validation strictly to environment/command-critical structural brackets: `[]` and `{}`. This significantly reduces false positives without compromising structural integrity checks.

## Translation Output Persistence
**The Problem:** The `download.py` route relied on a recursive `find` approach to locate `.pdf` files. In certain cases, translated `.tex` files generated intermediate dummy `2503.19300.pdf` files deep in source project folders alongside the true mapped translation (`zh_2503.19300_translated.pdf`). The API would incorrectly pick up and serve the raw English dummy file instead of the translation. Additionally, tasks lacked a persistent trail of state transitions for debugging because they relied entirely on ephemeral console stdout.

**Chosen Solution:**
- **Precise File Resolution:** Implement `_find_translated_pdf` in `download.py`. This explicitly checks the root of the task's output directory (`outputs/{task_id}/{lang_project_name}`) for any PDF ending with `_translated.pdf`. It explicitly avoids recursive descent into subdirectories (like the unpacked source folder) to ensure the served PDF is the final rendering.
- **Persistent State Logging:** Inject structured `_write_task_log` calls at key lifecycle stages in `CoordinatorAgent` (`workflow_latextrans_async`). These write JSON event entries to a `task_log.json` file pinned inside the task's specific output folder.

## Prompt Concurrency Isolation
**The Problem:** Concurrent translation processes (e.g., translating one document from English to Japanese while simultaneously translating another from English to Chinese) were mixing languages. Sentences would emerge half-Japanese, half-Chinese in the same PDF. The root cause was `prompts.py`, where `pm.init_prompts` mutated global string constants for system prompts.

**Chosen Solution:**
- **Thread-safe Factory:** Deprecate global reliance by introducing `create_prompts(source_lang, target_lang) -> dict` in `prompts.py`, guarded by a module-level `threading.Lock()`. This function temporarily updates globals under lock, then immediately snapshots them into a returned dictionary, eliminating race conditions.
- **Agent Refactoring:** Refactor the prompt handling in `TranslatorAgent` and `ParserAgent` (specifically `execute()` methods) to execute `self.prompts = pm.create_prompts(...)` on initiation. Exhaustively replace all references to `pm.` prompts within worker logic with robust isolated lookups (e.g., `self.prompts["section_system_prompt"]`), ensuring each task safely owns its prompt state.

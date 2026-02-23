# Incorporate User Feedback Optimizations

This change serves as a rolling update for minor front-end branding, UX improvements, and other optimizations collected from user feedback during the internal testing phase.

## Capabilities

### Update Website Branding and Metadata
- Update the document title to better reflect the purpose of the application.
- Add a favicon to improve the professional appearance and browser tab identification for the website.

### Robust Guest Task Cleanup
- Prevent storage leaks by implementing a robust cleanup mechanism for temporary/guest tasks that persists across backend restarts.
- Periodically scan output and terminology directories.
- Delete any task folders older than the guest TTL (e.g., 2 hours) that do not have a corresponding record in the Supabase `translation_tasks` table. 

### Email Notification on Task Completion
- Provide an advanced configuration option (toggle button) for users to request an email notification when all their tasks (or a large batch task) are completed.
- Utilize standard SMTP configuration in the backend to send robust, custom email notifications separate from Supabase Auth's restricted templates.

### ArXiv Download Optimization & Progress UI
- Throttle backend database I/O for arXiv downloads to prevent severe synchronization delays caused by updating progress on every data chunk.
- Overhaul the frontend download progress bar to use premium UI designs (animated shimmer effects, stage labels, smooth transitions) matching the rest of the application.

### Typography Parameter Bounds Validation
- Enforce safe ranges for advanced typography injection: font size `[8, 14]` pt, line spacing `[1.0, 2.5]`.
- Update backend (`utils.py`) to skip injection and issue warnings if values are out of bounds.
- Update frontend UI (`FormattingPanel.tsx`) to restrict inputs and provide precise tooltips explaining the valid ranges and fallback behavior.

### CJK Font Compatibility Fix
- Resolve critical XeLaTeX/ctex compilation failures (e.g., `nullfont` missing character errors) caused by custom document classes (like `atlasdoc.cls`) loading pdfLaTeX-specific font packages (`fontenc[T1]`, `newtxtext`, `newtxmath`).
- Extend `_comment_out_pdflatex_commands` to neutralize these specific font packages.
- Introduce `_patch_sibling_style_files` to scan and patch sibling `.cls` and `.sty` files in the output directory prior to rendering.

### Translation Intra-Section Parallelization
- Accelerate translation speed by parallelizing the LLM API calls within each section: the section body, its child environments, and its child captions SHALL be translated concurrently via `asyncio.gather` instead of sequentially awaited.
- Maintain the existing inter-section `Semaphore(10)` concurrency limit unchanged.
- Preserve correctness: each sub-element (section, env, caption) is an independent, context-free LLM request, so concurrent execution does not compromise translation quality.

### Global API Rate Limiting
- Introduce a centralized global `Semaphore` (e.g., `Semaphore(40)`) to enforce a hard architectural limit on concurrent external LLM API requests across the entire application (spanning all active tasks and all users).
- Prevent HTTP 429 Too Many Requests errors from strict external providers (like NVIDIA NIM free tiers, which enforce a 40 Request Per Minute limit).
- Ensure that local intra-section scaling does not collectively overwhelm the backend when multiple translation tasks are running simultaneously.

### LLM Timeout & Retry Robustness
- Fix a critical bug where asynchronous HTTP timeouts (`aiohttp`) were incorrectly caught using a synchronous exception type (`requests.exceptions.RequestException`), causing translation tasks to crash instead of retrying.
- Enhance all LLM API request methods in `TranslatorAgent` to use a 180-second timeout, exponential backoff for retries, and explicit handling for HTTP 429 (Too Many Requests) by respecting the `Retry-After` header.

### Legacy Verification Config Cleanup
- Remove residual references to the deprecated `enable_verification` field in `backend/app/api/routes/translate.py` to prevent `AttributeError` during task execution and configuration hashing.

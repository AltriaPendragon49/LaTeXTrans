# latex-translation-core Specification

## Purpose
定义 LaTeX 翻译核心引擎的技术和行为规范。本规范深入描述了从原始 LaTeX 结构化文档的内容解析到多 Agent（如 ParserAgent、TranslatorAgent、GeneratorAgent）协同处理的过程；涉及了大语言模型（LLM）对具体文本环境化内容的智能判定及重翻译逻辑；并详细规定了最终生成目标 PDF 时的编译流程、包括基于字符出现频率的智能排版引擎（XeLaTeX、LuaLaTeX、pdfLaTeX）切换和回退重试策略。
## Requirements
### Requirement: LaTeX Parsing and Translation

The system SHALL parse LaTeX source files into an Abstract Syntax Tree (AST), translate extracted text content while preserving structure, and reconstruct valid LaTeX output. **The system SHALL algorithmically enforce a maximum token length for all textual sections before transmission to the Language Model.**

#### Scenario: Single huge section chunking (NEW)
- **WHEN** a LaTeX document parsing yields a section whose content exceeds a predefined maximum token threshold (e.g., 4000 tokens)
- **THEN** the system SHALL divide the section into sequential sub-chunks
- **AND** the split SHALL primarily occur at natural paragraph boundaries (double newlines) to preserve semantic contexts natively
- **AND** the sub-chunks SHALL independently undergo translation without exceeding language model token limits.

#### Scenario: Extreme single paragraph fallback (NEW)
- **WHEN** an individual natural paragraph internally exceeds the maximum token threshold
- **THEN** the system SHALL apply a secondary splitting heuristic using sentence-terminating punctuation
- **AND** prioritize maintaining semantic integrity over exact character limits.

#### Scenario: Cross-chunk context preservation (Overlap context) (NEW)
- **WHEN** a section block is algorithmically divided into sequential sub-chunks
- **THEN** the system MUST extract the trailing segment (e.g., the last paragraph or sentence) of a preceding chunk
- **AND** pass it as read-only "Reference Context" to the language model when translating the subsequent chunk
- **AND** instruct the model to strictly ignore this context for output generation to prevent duplicated translation.

#### Scenario: Reference Context Prompt Isolation and Leakage Retry (NEW)
- **WHEN** Reference Context is passed to the translation language model
- **THEN** the context MUST be strictly isolated within the `system` prompt role
- **AND** MUST be wrapped in explicit XML tags (e.g., `<REFERENCE_CONTEXT>`)
- **AND** the system MUST execute post-translation validation to detect leaked markup or unmodified context copying
- **AND** if leakage is detected, MUST execute a single retry attempt.

#### Scenario: Context Downgrade Fallback (NEW)
- **WHEN** a translation sub-chunk triggers leakage detection repeatedly (failing the retry attempt)
- **THEN** the system MUST downgrade the translation request by structurally stripping the Reference Context from the prompt
- **AND** execute a final standalone translation request for the sub-chunk to guarantee compilation safety over contextual flow.

### Requirement: arXiv Source Download
The system SHALL download LaTeX source code from arXiv.org given a valid paper ID.

#### Scenario: CLI arXiv download (existing)
- **WHEN** user provides `--arxiv` argument to CLI
- **THEN** `batch_download_arxiv_tex()` downloads `.tar.gz` source to `tex source/` directory

#### Scenario: Web API arXiv download (new)
- **WHEN** backend receives `POST /arxiv` request with arXiv ID
- **THEN** adapted `batch_download_arxiv_tex()` downloads source to `data/uploads/{task_id}/` and returns task ID to caller

#### Scenario: arXiv metadata extraction (existing)
- **WHEN** downloading from arXiv
- **THEN** the system extracts paper category (e.g., "cs.AI") via `get_arxiv_category()` for potential terminology selection (unused in MVP, used in Phase 2)

### Requirement: LaTeX Compilation with Intelligent Fallback
The system SHALL compile translated LaTeX files with intelligent multi-engine fallback and MUST produce explicit structured outcomes for success and compilation failure.

#### Scenario: Timeout process-tree cleanup
- **WHEN** a compile subprocess exceeds timeout
- **THEN** the system MUST terminate the full process tree
- **AND** on Windows MUST use process-tree termination semantics (`taskkill /T /F`).

#### Scenario: Outdated local class-file conflict
- **WHEN** a project-bundled `.cls` file conflicts with system TeX distribution compatibility
- **THEN** the system MUST prefer the compatible system class file when safe resolution is available.

#### Scenario: Structured compilation failure result
- **WHEN** all engines fail to produce a valid translated PDF
- **THEN** the generator/coordinator pipeline MUST return structured failure fields including `status=failed_compilation` and `error_summary`
- **AND** MUST persist a `compilation_failed` event in `task_log.json` with diagnostic context.

#### Scenario: Engine fallback PDF path integrity
- **WHEN** multi-engine fallback runs on a project that contains stale pre-copied `<basename>.pdf` or later-engine clobber risk
- **THEN** each engine attempt MUST treat stale `<basename>.pdf` as invalid pre-run output
- **AND** the fallback selector MUST only return `pdf_path` values that still exist on disk at selection time.

#### Scenario: Relative output directory invocation
- **WHEN** compilation is invoked with a relative `output_dir` and engine subprocesses run with `cwd` set to the TeX directory
- **THEN** the compiler MUST normalize `output_dir` and `tex_file` to absolute paths before engine invocation
- **AND** MUST evaluate produced `pdf_path`/`log_path` against the same normalized absolute directory.

#### Scenario: Missing PDF with zero parsed errors
- **WHEN** a compile attempt exits without producing a PDF
- **AND** log parsing returns `error_count=0`
- **THEN** the compiler MUST synthesize a fallback compile error with exit-code context
- **AND** MUST report the compile attempt as failed (not success).

### Requirement: PDF Generation Readiness Verification

The system SHALL verify that generated PDF files are fully written and accessible before marking translation tasks as completed.

#### Scenario: PDF file verification after generation
- **WHEN** `GeneratorAgent` successfully compiles a PDF and moves it to the output directory
- **THEN** the system verifies the PDF file exists, has non-zero size, and contains a valid PDF header (`%PDF-`)
- **AND** only after verification passes, updates task progress to 100%

#### Scenario: PDF file verification during move operation
- **WHEN** `shutil.move()` is called to relocate the generated PDF
- **THEN** the system waits for the filesystem to fully commit the write operation
- **AND** verifies file accessibility by attempting to open and read the PDF header

#### Scenario: Preview endpoint PDF readiness check
- **WHEN** client requests `/preview/{task_id}/pdf` endpoint
- **THEN** the system checks that the PDF file has non-zero size and valid PDF header
- **AND** if the PDF is not ready (empty or invalid header), returns HTTP 503 with message "PDF generation in progress, please retry"

#### Scenario: Download endpoint PDF readiness check
- **WHEN** client requests `/download/{task_id}/pdf` endpoint
- **THEN** the system performs the same readiness check as the preview endpoint
- **AND** returns HTTP 503 if the PDF is not ready

#### Scenario: Handling filesystem race conditions
- **WHEN** the task status is "completed" but the PDF file is not yet readable
- **THEN** the preview/download endpoints return HTTP 503 (Service Unavailable) instead of HTTP 404 (Not Found)
- **AND** the response includes a "Retry-After" header suggesting client retry in 1-2 seconds

### Requirement: Validation Error Classification

The system SHALL classify validation errors into three categories with distinct handling strategies.

#### Scenario: A-type error detection (configuration/resource)
- **WHEN** `ValidatorAgent` encounters an error containing "not found", "missing", or "configuration"
- **THEN** the error report includes `error_type: "A"`
- **AND** the error triggers graceful degradation (e.g., load empty terminology table)

#### Scenario: B-type error detection (fixable syntax)
- **WHEN** `ValidatorAgent` encounters LaTeX syntax errors (unescaped special chars, misspelled commands)
- **AND** error does not match A-type or C-type patterns
- **THEN** the error report includes `error_type: "B"`
- **AND** the error is eligible for translation retry (max 1)

#### Scenario: C-type error detection (structural mismatch)
- **WHEN** `ValidatorAgent` encounters command_error containing pattern `expected \d+, found \d+`
- **OR** `ValidatorAgent` encounters a `math_delimiter_mismatch` error
- **OR** `ValidatorAgent` encounters residual `PROTECTED_CMD` text
- **THEN** the error report includes `error_type: "C"`
- **AND** the error is marked for algorithmic repair (not LLM retry)

### Requirement: Error-type-aware Retry Logic

The system SHALL route errors to appropriate handlers based on classification.

#### Scenario: B-type error translation retry
- **WHEN** `TranslatorAgent` processes errors with `error_type: "B"`
- **THEN** the system attempts `_retranslate_error_parts()` at most once
- **AND** if retry fails, marks part as failed

#### Scenario: C-type error algorithmic repair
- **WHEN** `TranslatorAgent` processes errors with `error_type: "C"`
- **THEN** the system invokes `apply_structural_fix()` without LLM call
- **AND** attempts to restore missing tokens from original content

#### Scenario: C-type repair fallback
- **WHEN** `apply_structural_fix()` cannot restore structural consistency
- **THEN** the system prioritizes preserving existing translated content if available
- **AND** falls back to original content only when translation is completely missing
- **AND** logs the failure with detailed mismatch information

### Requirement: Preamble Formatting Injection
系统 SHALL 在翻译完成、PDF 编译之前，根据用户的排版配置对 LaTeX 导言区执行自动化注入和修改。

#### Scenario: 行距配置注入
- **WHEN** 用户配置 `formatting.line_spacing` 为一个数值（如 `1.5`）
- **THEN** 系统在 `\begin{document}` 前注入 `\usepackage{setspace}` 和 `\setstretch{1.5}`
- **AND** 若 `setspace` 已存在则仅修改行距数值

#### Scenario: 全局字号替换
- **WHEN** 用户配置 `formatting.font_size` 为一个数值（如 `12`）
- **THEN** 系统通过正则将 `\documentclass` 中的字号选项替换为 `12pt`
- **AND** 若原 `\documentclass` 无字号选项则追加

#### Scenario: 栏模式切换 - 双栏转单栏
- **WHEN** 用户配置 `formatting.column_mode = "single"`
- **THEN** 系统移除 `\documentclass` 中的 `twocolumn` 选项
- **AND** 在 `\begin{document}` 后注入 `\onecolumn`

#### Scenario: 栏模式切换 - 单栏转双栏
- **WHEN** 用户配置 `formatting.column_mode = "double"`
- **THEN** 系统在 `\documentclass` 选项中添加 `twocolumn`
- **AND** 在 `\begin{document}` 后注入 `\twocolumn`

#### Scenario: 页边距配置
- **WHEN** 用户配置 `formatting.margin` 为 `"narrow"` / `"normal"` / `"wide"`
- **THEN** 系统注入 `\usepackage[margin=X]{geometry}`
- **AND** 若 `geometry` 已存在则替换其 margin 参数

#### Scenario: 中文首行缩进
- **WHEN** 用户配置 `formatting.paragraph_indent = true`
- **THEN** 系统注入 `\setlength{\parindent}{2em}`

#### Scenario: CJK 字体覆盖
- **WHEN** 用户配置 `formatting.cjk_font = "songti"` 或 `"heiti"`
- **AND** 目标语言为中文 (zh/ch)
- **THEN** 系统注入对应的 `\setCJKmainfont{...}` 命令

#### Scenario: 参考文献格式替换
- **WHEN** 用户配置 `formatting.bib_style` 为非 null 值
- **THEN** 系统查找现有 `\bibliographystyle{...}` 并替换为指定格式
- **AND** 若不存在 `\bibliographystyle` 则不注入

#### Scenario: 引文标记风格配置
- **WHEN** 用户配置 `formatting.cite_style = "super"`
- **THEN** 系统注入 `\usepackage[numbers,sort&compress]{natbib}` 并定义上标引用宏

#### Scenario: 图表标题本地化
- **WHEN** 用户配置 `formatting.localize_captions = true`
- **AND** 目标语言为中文
- **THEN** 系统注入 `\renewcommand{\figurename}{图}` 和 `\renewcommand{\tablename}{表}`

#### Scenario: 默认不注入
- **WHEN** `formatting` 配置为 `null` 或所有字段均为 null
- **THEN** 系统不修改 LaTeX 导言区
- **AND** 翻译行为与升级前完全一致

#### Scenario: 宏包冲突检测
- **WHEN** 注入的宏包在原文档中已存在
- **THEN** 系统替换其参数而非重复添加

### Requirement: Biblatex Backend Support
The system MUST correctly compile bibliographies for LaTeX documents that utilize the `biblatex` package, even when original `.bib` files are missing.

#### Scenario: Compiling with biblatex dependency and missing .bib
- **WHEN** a user translates an arXiv project using `biblatex` with incompatible `.bbl` files
- **THEN** the system MUST implement a Python-based fallback to extract `author`, `title`, and `year`
- **AND** automatically replace `\printbibliography` with a native `thebibliography` block.

### Requirement: CJK Font Compatibility Fix
The system MUST dynamically neutralize incompatible pdfLaTeX-specific font packages to ensure correct XeLaTeX rendering of CJK characters.

#### Scenario: Neutralizing conflicting font macro-packages
- **WHEN** the document class or local style files load `fontenc[T1]`, `newtxtext`, or `txfonts`
- **THEN** the system MUST comment out these commands in the main file and all local `.cls`/`.sty` files prior to compilation.

### Requirement: Intra-Section Translation Parallelization
The TranslatorAgent SHALL translate child environments and captions within each section concurrently using `asyncio.gather()`.

#### Scenario: Concurrent environment and caption translation
- **WHEN** a section contains multiple environments or captions
- **THEN** the system SHALL execute `_translate_env` and `_translate_caption` calls in parallel phases
- **AND** total processing time SHALL be optimized without missing captions discovered inside environments.

### Requirement: Global API Rate Limiting
The system SHALL implement a globally shared concurrency limit for all outbound LLM API requests.

#### Scenario: Enforcing global LLM concurrency
- **WHEN** multiple tasks or sub-tasks trigger LLM requests
- **THEN** they MUST acquire a global `asyncio.Semaphore` (default: 30)
- **AND** excess requests SHALL queue without blocking or timing out.

### Requirement: Translation Completeness Validation
The system MUST algorithmically verify that the translation output does not improperly skip or retain large blocks of source-language prose.

#### Scenario: Flagging incomplete translations
- **WHEN** the retention ratio of source-language English words exceeds 55%
- **THEN** the section MUST be flagged as an incomplete (Type T) error
- **AND** trigger an automated re-translation with explicit completeness instructions.

### Requirement: Robust LaTeX Syntax Validation
The system SHALL accurately identify LaTeX syntax errors without generating false positives for common document structures like numbered lists.

#### Scenario: Parentheses in enumerated lists ignored
- **WHEN** the system validates a document containing `(1)` or `1)` in an `enumerate` environment
- **THEN** it SHALL NOT flag these as unmatched brackets
- **AND** it SHALL only track `[]` and `{}` pairs for syntax validation.

### Requirement: Thread-Safe Prompt Isolation
The system SHALL isolate language prompt states across concurrent tasks to prevent race conditions.

#### Scenario: Isolated prompt instantiation
- **WHEN** a translation task begins
- **THEN** it MUST use `pm.create_prompts` under a threading lock to obtain an isolated dictionary of prompt templates
- **AND** all subsequent logic MUST use this instance-specific dictionary instead of global variables.

### Requirement: Persistent Task Logging
The system SHALL maintain a structural JSON log of critical task state transitions within the output directory.

#### Scenario: Writing task log events
- **WHEN** a task achieves a major milestone (parsing end, translation start, etc.)
- **THEN** the system SHALL append a JSON entry to `task_log.json` containing a timestamp, event name, and auxiliary data.

### Requirement: Placeholder Integrity and Recovery

The translation pipeline MUST aggressively protect and recover all injected placeholders (e.g., `<PLACEHOLDER_ENV_{ID}>`) to ensure zero leakage of placeholder tags into the final compiled PDF and zero misfires of translation reassembly logic.

#### Scenario: LLM escapes placeholders natively
- **Given** an LLM translates a segment and outputs `<$PLACEHOLDER_ENV_10$>` or `\textless PLACEHOLDER\_CAP\_1\textgreater` instead of the exact expected tag.
- **When** the coordinator processes the translated text prior to checking for missing placeholders (`_fix_missing_placeholders`) and prior to the environment/caption substitution step (`reconstruct.py`).
- **Then** the `restore_mangled_placeholders` utility MUST execute a fuzzy regex scan against the list of known original placeholders for that segment.
- **And** it MUST perfectly restore the escaped/wrapped text back into the standard exact string (e.g. `<PLACEHOLDER_ENV_10>`) to proceed normally.

#### Scenario: Proper tags remain untouched
- **Given** an LLM correctly preserves the exact tag `<PLACEHOLDER_ENV_10>`.
- **When** the translated text is processed by `restore_mangled_placeholders`.
- **Then** the text MUST remain completely untouched and valid, preventing any double-formatting or greedy-regex collateral damage.

### Requirement: API Fatal Error Fast-Fail

The system MUST short-circuit arbitrary retry backoff delays immediately upon encountering deterministic client or authentication errors from the LLM provider.

#### Scenario: Encountering a 404 or 401 error
- **WHEN** the `TranslatorAgent` or any sub-function calls the LLM completions API and receives an `aiohttp.ClientResponseError` with a status of 400, 401, 403, or 404
- **THEN** the system MUST NOT enter the progressive exponential backoff loop (e.g., 5s, 10s, 20s)
- **AND** it MUST immediately flag that segment as failed, log the fatal error exclusively, and return control backwards to avoid UI-blocking polling loops.
- **AND** the translation output for the failed segment drops back to text preservation or degraded returns directly.

### Requirement: Display-Math Delimiter Preservation During Reconstruction
The system SHALL preserve source display-math delimiter semantics during reconstruction to avoid invalid math environment combinations.

#### Scenario: Source uses bracketed display math but translation uses dollar delimiters
- **WHEN** source fragment contains `\[` and `\]`
- **AND** translated fragment replaces these with paired `$$`
- **THEN** reconstruction MUST restore paired `$$` back to `\[` and `\]` in order.

#### Scenario: Source does not use bracketed display math
- **WHEN** source fragment has no `\[`/`\]`
- **THEN** the restoration logic MUST NOT force delimiter replacement.

#### Scenario: Unpaired or ambiguous dollar delimiters
- **WHEN** translated fragment contains unmatched/odd `$$`
- **THEN** reconstruction MUST degrade safely (no exception) and preserve remaining text.

#### Scenario: Malformed display-math shell compared with valid source shell
- **WHEN** translated fragment has malformed display-math shell state (e.g., unclosed/mixed `$$`, `\[` and `\]`)
- **AND** the source fragment shell is structurally valid
- **THEN** reconstruction MUST keep the translated content (to prioritize target-language persistence) and log a warning.

#### Scenario: Inline-math restoration must not capture display math
- **WHEN** inline `$...$` restoration is applied to translated content
- **THEN** the matcher MUST NOT treat `$$...$$` delimiters as inline math boundaries
- **AND** MUST preserve display-math delimiter integrity.

### Requirement: Tag Command Context Preservation During Reconstruction
The system SHALL preserve source `\tag{...}` semantics and MUST prevent translated `\tag` commands from escaping display-math context.

#### Scenario: Source tag dropped by translation
- **WHEN** source fragment contains one or more `\tag{...}` commands
- **AND** translated fragment drops those tags
- **THEN** reconstruction MUST append missing source tags to the end of the translated fragment instead of reverting to source content.

#### Scenario: Translated tag moves outside display-math context
- **WHEN** translated fragment contains `\tag{...}` outside any display-math context
- **AND** source fragment does not contain out-of-context tags
- **THEN** reconstruction MUST keep the translated content (to prioritize target-language persistence).

#### Scenario: Source has no tag command
- **WHEN** source fragment contains no `\tag{...}` commands
- **AND** translated fragment introduces `\tag{...}`
- **THEN** reconstruction MUST remove those translated tags.

### Requirement: Environment Wrapper and Header-Math Preservation During Reconstruction
The system SHALL preserve source environment shell structure and MUST prevent fatal header-level math token breakage introduced by translation.

#### Scenario: Missing environment begin/end wrappers in translated block
- **WHEN** source fragment is an environment block and translated fragment loses `\begin{env}` or `\end{env}`
- **THEN** reconstruction MUST restore source-compatible begin/end wrappers around the translated body
- **AND** MUST keep translated body content whenever non-empty.

#### Scenario: Unsafe translated environment header after math delimiter loss
- **WHEN** source environment header contains inline math delimiters
- **AND** translated header drops delimiters and leaves unsafe `_` or `^` tokens
- **THEN** reconstruction MUST first attempt translated-header repair by wrapping math-like tokens into inline math
- **AND** MUST fallback to the source begin-header command only if translated header remains unsafe.

#### Scenario: Wrapper repair fallback when translated body is empty
- **WHEN** wrapper restoration is required and translated body content is empty
- **THEN** reconstruction MUST fallback to the source body content to keep environment syntactically valid.

#### Scenario: Unsafe translated inner environment wrapper
- **WHEN** translated environment content is fully wrapped by a non-ASCII/unsafe inner `\begin{...}` `\end{...}` pair
- **THEN** reconstruction MUST strip the unsafe inner wrapper
- **AND** MUST preserve the translated body text inside the original source-compatible outer environment.

### Requirement: Sectioning Command-Structure Preservation During Reconstruction
The system SHALL preserve sectioning command shells and MUST repair unsafe heading math-token drift introduced by translation.

#### Scenario: Sectioning command sequence mismatch
- **WHEN** source and translated fragments contain different sectioning command sequences (`\section`, `\subsection`, etc.)
- **THEN** reconstruction MUST fallback the section fragment to source content.

#### Scenario: Malformed sectioning command argument structure
- **WHEN** translated sectioning commands have malformed required argument groups
- **THEN** reconstruction MUST fallback the section fragment to source content.

#### Scenario: Source heading contains math but translated heading drops delimiters
- **WHEN** source heading argument contains inline math
- **AND** translated heading argument drops `$...$` but contains unsafe `_`/`^` tokens
- **THEN** reconstruction MUST first attempt to wrap likely math tokens with inline delimiters
- **AND** MUST fallback to source heading command only if repaired heading remains unsafe.

### Requirement: Custom Macro Shell Preservation During Reconstruction
The system SHALL preserve argument shells for sensitive custom macro commands used in math papers.

#### Scenario: twopartpiecewise command shell drift
- **WHEN** source fragment contains `\twopartpiecewise{...}{...}{...}{...}`
- **AND** translated fragment keeps command count and placement
- **THEN** reconstruction MUST replace translated command calls with source command calls by occurrence order.

#### Scenario: twopartpiecewise command is dropped or count-mismatched
- **WHEN** translated fragment drops `\twopartpiecewise` commands or changes command count
- **THEN** reconstruction MUST replace matched commands and append remaining source commands while preserving translated text, instead of falling back the entire fragment.

### Requirement: Document Tail Completion Safety
The system SHALL ensure reconstructed output ends with a structurally complete document tail.

#### Scenario: Missing \end{document} with recoverable source anchor
- **WHEN** translated reconstructed content misses `\end{document}`
- **AND** source main tex contains a recoverable late anchor (`\bibliographystyle`, `\bibliography`, `\begin{thebibliography}`, or `\appendix`)
- **THEN** reconstruction MUST splice the source tail from the latest matching anchor.

#### Scenario: Missing \end{document} without recoverable anchor
- **WHEN** translated reconstructed content misses `\end{document}`
- **AND** no safe source anchor can be matched
- **THEN** reconstruction MUST append missing closing braces and `\end{document}` as fallback.

### Requirement: Label-Key Preservation During Reconstruction
The system SHALL preserve source `\label{...}` keys during reconstruction to maintain cross-reference integrity.

#### Scenario: Translated label key is mutated
- **WHEN** translated fragment contains `\label{...}` keys that differ from source keys (e.g., punctuation mutation)
- **THEN** reconstruction MUST restore source label commands deterministically by occurrence order.

#### Scenario: Translated fragment drops labels
- **WHEN** source fragment contains one or more `\label{...}` commands but translated fragment contains none
- **THEN** reconstruction MUST append missing source labels as a safe fallback.

### Requirement: Caption Command-Structure Preservation During Reconstruction
The system SHALL preserve caption command wrappers so translated references remain resolvable.

#### Scenario: Caption command wrapper is dropped in translation
- **WHEN** source caption fragment contains `\caption{...}`, `\subcaption{...}`, or `\captionof{...}{...}`
- **AND** translated caption fragment drops one or more of those command wrappers
- **THEN** reconstruction MUST fallback that caption fragment to source command structure.

#### Scenario: Caption command argument structure is malformed
- **WHEN** translated caption fragment contains caption commands with malformed required argument groups
- **THEN** reconstruction MUST fallback that caption fragment to source command structure.

#### Scenario: Caption command structure remains valid
- **WHEN** translated caption fragment preserves caption command wrappers and valid argument structure
- **THEN** reconstruction MUST keep translated caption content.

### Requirement: Sensitive Command Pre-Translation Protection
The system SHALL mask LaTeX commands whose arguments are structurally sensitive and MUST NOT be translated, before sending content to the LLM, and SHALL restore them after translation.

#### Scenario: ACM ccsdesc command protection
- **WHEN** source content contains `\ccsdesc[...]{...}` commands
- **THEN** the system MUST replace each matched command with an opaque placeholder before LLM translation
- **AND** MUST restore the original command after translation completes.

#### Scenario: CCSXML environment protection
- **WHEN** source content contains `\begin{CCSXML}...\end{CCSXML}` blocks
- **THEN** the system MUST replace the entire environment block with a single placeholder before LLM translation
- **AND** MUST restore the original block after translation completes.

#### Scenario: Retranslation protection for structural errors
- **WHEN** a translation falls back to retranslation due to structural errors
- **THEN** the system MUST apply sensitive command protection across the combined `[Original]/[Translation]/[Error]` prompt string
- **AND** MUST unmask the output from the LLM before returning the retranslated content.

#### Scenario: Configurable protection registry
- **WHEN** a new sensitive command pattern is identified (e.g., from compilation failure analysis)
- **THEN** the system MUST support adding it to the `PROTECTED_COMMANDS` registry without code changes to the translation pipeline.

#### Scenario: Protection action logging
- **WHEN** one or more commands are masked during translation
- **THEN** the system MUST log a structured JSON record of all masked commands per task for maintenance tracking.

### Requirement: API Rate Limit Resilience (429 Handling)
The translation service SHALL handle API rate limits (HTTP 429) gracefully with infinite retry and graduated backoff while maintaining system concurrency.

#### Scenario: Concurrent project isolation during 429 wait
- **WHEN** a translation sub-task hits a 429 error
- **THEN** the system MUST release the global LLM concurrency slot (semaphore) before sleeping
- **AND** MUST resume only after the backoff period expires.

#### Scenario: Graduated backoff strategy
- **WHEN** consecutive 429 errors occur for the same request
- **THEN** the system MUST follow a graduated retry strategy:
  - **Hits 1-3**: Quick retry using `Retry-After` header or default 10s.
  - **Hits 4-9**: Progressive delay (35s to 60s).
  - **Hits >9**: Infinite wait with a fixed 60s interval.

#### Scenario: User notification for persistent rate-limiting
- **WHEN** 429 hits exceed 9 consecutive attempts
- **THEN** the agent MUST push a progress update with a specific rate-limit warning message to the task manager.

#### Scenario: Infinite retry semantics
- **WHEN** a 429 error occurs
- **THEN** the system MUST NOT return the original text or fail the task solely due to rate limits
- **AND** MUST loop until success is achieved or a non-429 fatal error occurs.

### Requirement: PDF Page Dimensions and Overflow Prevention for CJK
The system SHALL ensure that translated CJK documents have correct physical page dimensions and MUST prevent content truncation caused by Latin-centric layout packages.

#### Scenario: Replace a4wide with geometry for CJK
- **WHEN** a LaTeX document uses the `a4wide` package (standalone or in a combo `\usepackage{...}`)
- **AND** the target language is a CJK language (zh, ja, ko)
- **THEN** the system MUST replace `a4wide` with `\usepackage[a4paper, left=2cm, right=2cm, top=2.5cm, bottom=2.5cm]{geometry}`
- **OR** if `geometry` is already present, MUST ensure the `a4paper` option is added and `a4wide` is removed.

#### Scenario: Inject raggedbottom for CJK pagination
- **WHEN** the target language is a CJK language (zh, ja, ko)
- **THEN** the system MUST inject `\raggedbottom` before `\begin{document}` to prevent vertical stretching and page overflow.

[Checklist: Delta validation]
- [x] Delimiter restoration covers sections/envs/captions
- [x] Environment wrapper/header-math repair covers env reconstruction path
- [x] Label-key preservation applied in reconstruction path
- [x] 429 handling releases semaphore during sleep
- [x] Backoff strategy is graduated (3 stages)
- [x] Progress updates are emitted after 9 hits
- [x] _fix_page_overflow_for_cjk implemented in utils.py
- [x] a4wide combo-package replacement handled correctly
- [x] \raggedbottom injected correctly for CJK
- [x] Display-math shell malformed fallback integrated in reconstruction
- [x] Out-of-context \tag detection and fallback integrated
- [x] Sectioning command-shell repair integrated
- [x] \twopartpiecewise shell restoration integrated
- [x] Document-tail restoration integrated before final write
- [x] Inline-math regex excludes $$...$$ display blocks
- [x] No-PDF/0-error fallback compile normalization implemented

### Requirement: Non-Translatable Environment Exclusion

The system SHALL preserve designated structural environments verbatim without sending their contents to the LLM for translation.

#### Scenario: CCSXML environment exclusion
- **WHEN** the parser encounters a `\begin{CCSXML}...\end{CCSXML}` block
- **THEN** the entire block SHALL be preserved verbatim in the translated output
- **AND** its contents SHALL NOT be sent to the LLM

#### Scenario: Verbatim and code environments exclusion
- **WHEN** the parser encounters `verbatim`, `lstlisting`, `minted`, `filecontents`, `filecontents*`, or `comment` environments
- **THEN** the entire block SHALL be preserved verbatim
- **AND** its contents SHALL NOT be sent to the LLM

#### Scenario: Selective nested placeholder translation
- **WHEN** an environment contains `PLACEHOLDER_CAP` or `PLACEHOLDER_ENV` tags
- **AND** the environment is one of: `frontmatter`, `abstract`, `title`, `author`, `keywords`
- **THEN** the system SHALL proceed with translation of the container content
- **AND** standard placeholder protection SHALL be applied to nested tags.

### Requirement: Resilient Protected Command Placeholder Restoration

The system SHALL restore PROTECTED_CMD placeholders after LLM translation, tolerating common LLM mutations to the placeholder format.

#### Scenario: Exact placeholder restoration
- **WHEN** `unmask_sensitive_commands` processes translated content containing `<PROTECTED_CMD_0>`
- **THEN** the placeholder SHALL be replaced with the original command from the mapping

#### Scenario: LLM-mutated placeholder restoration
- **WHEN** the LLM modifies the placeholder format to `\protect\PROTECTED_CMD_0`, `\\PROTECTED_CMD_0`, `{\PROTECTED_CMD_0}`, or adds whitespace
- **THEN** `unmask_sensitive_commands` SHALL still recognize and restore the placeholder

#### Scenario: Residual placeholder detection
- **WHEN** after unmask restoration, any `PROTECTED_CMD` text remains in the output
- **THEN** the system SHALL attempt force-restoration by positional order from the mapping
- **AND** log a warning for traceability

#### Scenario: Validator residual check
- **WHEN** `ValidatorAgent` validates a translated part
- **THEN** it SHALL additionally check for any remaining `PROTECTED_CMD` text in the translation
- **AND** flag it as a Type C structural error if found

### Requirement: CTeX Package Conflict Auto-Resolution

The system SHALL detect and resolve command name conflicts between the injected `ctex` package and author-defined commands before compilation.

#### Scenario: Detecting \I command conflict
- **WHEN** the original preamble contains `\newcommand{\I}` or `\renewcommand{\I}` or `\def\I`
- **AND** the system injects `\usepackage{ctex}` for Chinese translation
- **THEN** the system SHALL inject `\let\I\relax` before the ctex import to prevent "Command already defined" errors

#### Scenario: No conflict present
- **WHEN** the original preamble does not define any commands that conflict with ctex
- **THEN** no conflict-resolution injection SHALL occur

### Requirement: Package-Aware Engine Selection

The system SHALL optimize compilation engine selection based on detected package compatibility constraints.

#### Scenario: Skipping lualatex for xypdf documents
- **WHEN** the document preamble includes the `xypdf` package (via `\usepackage{xypdf}` or `xy` package with `pdf` option)
- **THEN** the system SHALL skip `lualatex` from the engine fallback order
- **AND** log the reason for the engine skip

### Requirement: Engine-Specific Compilation Logging

The system SHALL preserve compilation logs for each attempted engine run without overwriting previous attempts to maintain a full diagnostic audit trail.

#### Scenario: Storing lualatex log before fallback
- **WHEN** `lualatex` compilation fails
- **THEN** the system SHALL rename `main.log` to `main.lualatex.log` (or equivalent) before attempting fallback engines.

### Requirement: CJK-Aware Engine Prioritization and Exclusion

The system SHALL prioritize CJK-compatible engines (`lualatex`, `xelatex`) for CJK documents and exclude `pdflatex` results from high-quality selection if superior alternatives exist.

#### Scenario: CJK-aware engine prioritization and exclusion
- **WHEN** `target_language` is "ja", "zh", or "ko"
- **THEN** it SHALL prioritize `lualatex` or `xelatex` and use `pdflatex` only as the final fallback
- **AND** if a PDF was generated by modern engines, the `pdflatex` result SHALL be EXCLUDED from selection.

#### Scenario: Latin-script engine priority maintenance
- **WHEN** `target_language` is a Latin-script language (en, de, fr, es, it, pl, nl)
- **THEN** the system SHALL maintain the standard multi-engine priority loop
- **AND** `pdflatex` SHALL remain a primary candidate for compilation.

### Requirement: Precise Preamble Definition Extraction

The system SHALL correctly extract and preserve `\newenvironment` definitions including both begin and end code blocks without truncation.

#### Scenario: Extracting two-block environments
- **WHEN** the parser extracts a `\newenvironment{name}{begin-code}{end-code}` definition
- **THEN** it SHALL capture the entire definition into the `<PLACEHOLDER_NEWCOMMAND_N>`
- **AND** the end-code block SHALL NOT be left behind as stray text

### Requirement: Severe Translation Corruption Detection

The system SHALL detect severe structural corruption in inline mathematical contexts, even if delimiter counts match.

#### Scenario: Catching malformed inline math combinations
- **WHEN** translated inline math contains unbalanced structural braces (`\{`, `\}`) or untranslated trailing English fragments
- **THEN** the system SHALL flag this as a Type C (structural) error despite matching `$` counts.

### Requirement: Unified Language-Specific Package Mapping
The system SHALL configure LaTeX packages based on the target translation language following a strict architecture: **Language determines the package. Engines are dumb executors.**

#### Scenario: Japanese document compilation
- **WHEN** the target language is `ja`
- **THEN** the system MUST inject the `luatexja` package
- **AND** MUST NOT inject `xeCJK` or manual font configurations
- **AND** SHOULD apply `_fix_page_overflow_for_cjk` mitigations

#### Scenario: Korean document compilation
- **WHEN** the target language is `ko`
- **THEN** the system MUST inject the `kotex` package
- **AND** MUST NOT comment out pdfLaTeX font/encoding primitive commands (Zero-Touch for non-XeLaTeX packages)
- **AND** SHOULD apply `_fix_page_overflow_for_cjk` mitigations

#### Scenario: Chinese document compilation
- **WHEN** the target language is `zh` or `ch`
- **THEN** the system MUST inject `\usepackage[UTF8]{ctex}`
- **AND** MAY comment out pdfLaTeX commands for legacy `ctex` compatibility
- **AND** SHOULD apply `_fix_page_overflow_for_cjk` mitigations

#### Scenario: Latin-script/English document compilation
- **WHEN** the target language is `en`, `de`, `fr`, `es`, `it`, etc.
- **THEN** the system MUST NOT modify the document preamble's existing font, encoding, or pdfLaTeX primitive commands (Zero-Touch)
- **AND** MUST NOT call `_comment_out_pdflatex_commands`

### Requirement: Typed Invariant Violations for Forbidden Repair Paths
Speculative repair entrypoints that remain for compatibility MUST be sealed by typed invariant exceptions.

#### Scenario: Forbidden repair function is called
1. Given runtime reaches a sealed speculative repair function
2. When the function is invoked
3. Then it MUST raise a typed invariant exception
4. And the exception MUST include a stable error code for observability/replay.


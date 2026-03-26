# web-ui Specification

## Purpose
定义 LaTeXTrans 前端 Web UI 规范，包括 Dashboard、翻译配置、进度监控、PDF 预览等界面。
## Requirements
### Requirement: Responsive Web Dashboard
The system MUST provide a responsive web-based translation workspace while allowing the product homepage to become a community browse surface.

#### Scenario: User navigates to the translation workspace
Given the backend server is running
When the user accesses `/translate`
Then the Dashboard page should be displayed
And a prominent input field for ArXiv ID should be visible
And shared sidebar navigation should remain available

### Requirement: Translation Configuration
The system MUST allow users to configure translation parameters via the UI.

#### Scenario: User configures translation settings
Given the user is on the Dashboard
When the user selects "Source Language" and "Target Language"
And the user expands the "Advanced Settings" panel
Then they should be able to input API keys and set file paths
And they should be able to upload a custom terminology file

### Requirement: Real-time Progress Monitoring
The system MUST display real-time progress of the translation task.

#### Scenario: User starts a translation
Given valid configuration is entered
When the user clicks "Translate Now"
Then the view should switch to the "Processing Status" page
And a progress stepper acting as a timeline should update
And real-time logs from the backend should be displayed in a console view

### Requirement: Dual PDF Preview
The system MUST provide a comprehensive PDF preview and comparison tool.

#### Scenario: Translation completes successfully
Given the translation task has finished
When the user navigates to the "Preview" tab
Then they should see a split-screen view
And the left pane should display the original PDF
And the right pane should display the translated PDF

### Requirement: Advanced Configuration Panel
前端 SHALL 在 Dashboard 页面提供完整的高级配置面板，包含翻译模式、编译策略、术语表生成等选项。

#### Scenario: 配置使用作者默认API
- **WHEN** 用户在 Dashboard 高级配置面板查看功能开关区域
- **THEN** 系统显示两个并排的 toggle 卡片：
  - 「使用作者默认 API」toggle（左侧）
  - 「生成术语表」toggle（右侧）
- **AND** 无"验证代理"选项

### Requirement: Drag and Drop Upload Zone
前端 SHALL 在 Dashboard 页面提供拖拽上传区域，支持文件夹和压缩包上传。

#### Scenario: 显示拖拽区域
- **WHEN** 用户访问 Dashboard 页面
- **THEN** 页面显示明显的拖拽区域
- **AND** 区域包含"拖拽 LaTeX 文件夹或压缩包到此处"提示

#### Scenario: 拖拽文件进入
- **WHEN** 用户将文件拖拽进入上传区域
- **THEN** 区域边框变为高亮颜色
- **AND** 显示"释放以上传"提示

#### Scenario: 释放文件并显示预览
- **WHEN** 用户在上传区域释放拖拽的文件
- **THEN** 系统显示文件信息预览
- **AND** 显示文件/文件夹名称、文件数量、是否检测到 .tex 文件

### Requirement: Terminology Table Viewer
前端 SHALL 在翻译结果页面提供术语表查看组件。

#### Scenario: 查看术语表
- **WHEN** 用户点击结果页的"术语表"按钮
- **THEN** 系统显示侧边栏，展示术语对照列表
- **AND** 列表包含原文术语和译文术语两列

#### Scenario: 下载术语表
- **WHEN** 用户点击"下载 CSV"按钮
- **THEN** 系统下载 CSV 格式的术语表文件

### Requirement: ArXiv Download Progress Bar
鍓嶇 SHALL 鍦?Dashboard 椤甸潰鐨?Load Source 鎸夐挳涓嬫柟鏄剧ず涓嬭浇杩涘害鏉★紝鍙嶆槧鐪熷疄鐨勫悗绔笅杞借繘搴︺€?

#### Scenario: 鐐瑰嚮 Load Source 鍚庢樉绀鸿繘搴︽潯
- **WHEN** 鐢ㄦ埛鍦?arXiv ID 杈撳叆妗嗚緭鍏ユ湁鏁?ID 骞剁偣鍑?"Load Source" 鎸夐挳
- **THEN** 绯荤粺绔嬪嵆鍦ㄦ寜閽笅鏂规樉绀鸿繘搴︽潯缁勪欢
- **AND** 杩涘害鏉″垵濮嬪€间负 0%
- **AND** 鎸夐挳鐘舵€佸彉涓虹鐢?

#### Scenario: 杩涘害鏉″疄鏃舵洿鏂?
- **WHEN** 鍚庣杩斿洖涓嬭浇杩涘害鏇存柊锛堥€氳繃杞 /api/task/{task_id}锛?
- **THEN** 杩涘害鏉″钩婊戞洿鏂板埌鏈€鏂拌繘搴﹀€?
- **AND** 杩涘害鏉′笅鏂规樉绀哄綋鍓嶉樁娈垫弿杩帮紙濡?姝ｅ湪涓嬭浇 TeX 婧愮爜..."锛?

#### Scenario: 涓嬭浇瀹屾垚鍚庨殣钘忚繘搴︽潯
- **WHEN** 鍚庣杩斿洖 progress: 100 涓?status: "pending"
- **THEN** 杩涘害鏉℃秷澶?
- **AND** 鏄剧ず "Source Ready" 鎴愬姛鎻愮ず
- **AND** "Start Translation" 鎸夐挳鍙樹负鍙敤

#### Scenario: 涓嬭浇澶辫触鏃舵樉绀洪敊璇?
- **WHEN** 鍚庣杩斿洖 status: "failed"
- **THEN** 杩涘害鏉″彉涓虹孩鑹?閿欒鐘舵€?
- **AND** 鏄剧ず閿欒娑堟伅
- **AND** 鎻愪緵閲嶈瘯鎸夐挳

#### Scenario: SSE complete event with failed terminal status
- **WHEN** frontend receives SSE `complete` event
- **AND** event payload status is `failed`, `failed_compilation`, or `structure_invalid`
- **THEN** frontend MUST transition to failed download state
- **AND** frontend MUST NOT show success toast or `Source Ready`.

### Requirement: Progress Bar Visual Design
进度条 SHALL 遵循 ui-ux-pro-max 设计规范，提供专业的视觉效果。

#### Scenario: 进度条样式
- **GIVEN** 进度条组件渲染在页面上
- **THEN** 进度条高度为 8px
- **AND** 使用圆角设计（rounded-full）
- **AND** 背景色为 muted，前景色为 primary
- **AND** 进度变化带有平滑过渡动画（duration-300）

#### Scenario: 暗色模式兼容
- **GIVEN** 用户启用暗色模式
- **WHEN** 进度条显示
- **THEN** 进度条颜色适配暗色主题
- **AND** 文字对比度符合 WCAG AA 标准（≥4.5:1）

#### Scenario: 无障碍访问
- **GIVEN** 进度条组件渲染
- **THEN** 组件包含 aria-valuenow、aria-valuemin、aria-valuemax 属性
- **AND** 包含 role="progressbar" 属性
- **AND** 屏幕阅读器可正确读取进度百分比

### Requirement: Session Continuity for Temporary Users

The system SHALL allow temporary users to create multiple translation tasks without page refresh.

#### Scenario: New translation after completion
- **WHEN** user clicks "New Translation" button after task completion
- **THEN** frontend resets all task-related state (taskId, status, progress)
- **AND** closes any active SSE connection
- **AND** returns to initial file upload view

#### Scenario: New translation after failure
- **WHEN** user clicks "New Translation" button after task failure
- **THEN** frontend performs same state reset as completion scenario
- **AND** user can immediately start new upload/arXiv download

### Requirement: SSE-based Status Subscription

The system SHALL use Server-Sent Events for real-time status updates.

#### Scenario: SSE connection for task monitoring
- **WHEN** user starts a translation task
- **THEN** frontend establishes SSE connection to `/api/task/{task_id}/stream`
- **AND** updates UI immediately upon receiving events

#### Scenario: SSE fallback to polling
- **WHEN** SSE connection fails or is not supported
- **THEN** frontend falls back to `setInterval` polling at 2-second intervals
- **AND** user experience remains consistent

### Requirement: Reduced API Request Volume
The frontend MUST NOT generate more than 2 status queries per second during download operations.

#### Scenario: Request rate under normal SSE
- **WHEN** SSE connection is active
- **THEN** no polling requests SHALL be made
- **AND** API request rate SHALL be zero for status queries

#### Scenario: Request rate under fallback polling
- **WHEN** using fallback polling mode
- **THEN** polling interval SHALL be at least 2000ms
- **AND** API request rate SHALL NOT exceed 0.5 requests per second

### Requirement: Interactive Dismissible Tips

前端 SHALL 在 Dashboard 页面提供交互式提示框，用于引导用户并平衡页面空间，支持手动快速影藏。

#### Scenario: 提示框显示与点击消失
- **GIVEN** Dashboard 页面加载
- **WHEN** 对应的显示状态为真（默认每次加载为真）
- **THEN** 页面显示相关的 Info Tip（如 ArXiv 下载耗时提示、Nvidia API 性能预警）
- **WHEN** 用户点击提示框任何区域
- **THEN** 提示框通过渐隐缩放动画（fade-out & zoom-out）消失
- **AND** 该提示框在本次页面会话期间不再出现

#### Scenario: 悬停显示关闭反馈
- **GIVEN** 提示框处于显示状态
- **WHEN** 用户将鼠标悬停在提示框上方
- **THEN** 提示框背景色产生微弱变化（交互反馈）
- **AND** 提示框右侧显示 `X` 关闭图标，提示该区域可点击影藏

### Requirement: API Quality and Performance Warnings

前端 SHALL 在翻译配置面板显式提醒默认 API 的性能局限，引导用户进行优化设置。

#### Scenario: 显示 Nvidia 免费 API 警告
- **GIVEN** Dashboard 页面加载
- **THEN** 在 "Advanced Configuration" 栏右侧显示琥珀色（Amber）警告标签
- **AND** 文本告知用户默认 API 为英伟达免费层级，可能影响质量和速度
- **AND** 该警告标签支持交互式点击消失逻辑

### Requirement: Formatting Configuration Panel
前端 SHALL 在 Advanced Settings 面板中提供"排版与文献设置"折叠区，允许用户配置翻译后 PDF 的排版格式，并对关键数值执行范围限制。

#### Scenario: 展开排版配置面板
- **WHEN** 用户在 Advanced Settings 中点击"排版与文献设置"折叠项
- **THEN** 系统显示排版配置表单，包含以下选项组：
  - 版面设置：行距、字号、栏模式、页边距
  - 中文排版：字体、首行缩进（仅中文目标语言时显示）
  - 文献引用：参考文献格式、引文标记风格
  - 其他：图表标题本地化

#### Scenario: 行距和字号数值限制与输入
- **WHEN** 用户查看行距或字号配置项
- **THEN** 显示为一个启用/禁用按钮
- **AND** 启用后出现数字输入框
- **AND** 前端 MUST 限制字号在 `[8, 14]` 范围内，行距在 `[1.0, 2.5]` 范围内
- **AND** 提供解释性 Tooltip 指示这些范围
- **AND** 禁用时恢复为"保持原样"

#### Scenario: 栏模式支持双向切换
- **WHEN** 用户查看栏模式配置项
- **THEN** 显示下拉选项：保持原样 / 单栏 / 双栏

#### Scenario: 配置默认为"保持原样"
- **WHEN** 用户首次打开排版配置面板
- **THEN** 所有选项默认值为"保持原样"
- **AND** 若用户系统设置中有 `default_formatting` 则使用其值填充

#### Scenario: 目标语言联动显示
- **WHEN** 用户选择的目标语言为中文 (zh/ch)
- **THEN** 显示"中文字体"和"首行缩进"选项
- **AND** "图表标题本地化"选项可用

#### Scenario: 排版配置随翻译请求提交
- **WHEN** 用户修改排版配置并点击翻译按钮
- **THEN** 排版配置序列化为 `advanced_config.formatting` JSON 字段
- **AND** 随翻译请求一同提交到后端 API

#### Scenario: 排版配置在批量翻译中共享
- **WHEN** 用户切换到 Batch Tab
- **THEN** 排版配置面板仍然可见且配置对批量任务统一生效

### Requirement: Web UI Branding
The application MUST display professional branding, including a descriptive `<title>` and a unique favicon.

#### Scenario: Browser tab branding
- **WHEN** a user opens or bookmarks the website
- **THEN** they MUST see the application title and favicon in the browser tab.

### Requirement: Premium Download Progress UI
The frontend MUST display an interactive and premium progress bar according to ui-ux-pro-max guidelines.

#### Scenario: Interactive progress bar with shimmer
- **WHEN** a task is in progress
- **THEN** the progress bar MUST display an animated shimmer effect
- **AND** show pulsing status indicators and stage descriptors.

### Requirement: Email Notification Configuration
The UI SHALL allow users to configure email notifications for task events.

#### Scenario: Enabling completion emails
- **WHEN** a user opens Advanced Configuration
- **THEN** they MUST see a toggle switch for "发送邮件通知 (完成时)" 
- **AND** activating it MUST bind the preference to the task payload.

### Requirement: Required Frontend API Base Environment Variable
Frontend MUST require `VITE_API_BASE_URL` for all API calls.

#### Scenario: Shared resolver enforces API base env
- **WHEN** frontend initializes API client or API-consuming pages
- **THEN** API base URL MUST be loaded from a shared resolver bound to `VITE_API_BASE_URL`
- **AND** missing value MUST throw an explicit configuration error

### Requirement: Frontend Public Key Boundary
Frontend env MUST include only publishable Supabase keys.

#### Scenario: Frontend env excludes service-role key
- **WHEN** frontend `.env*` files are used
- **THEN** only public Supabase keys (URL + anon/publishable) MAY appear
- **AND** service-role key MUST NOT appear in any `VITE_*` variable

### Requirement: User-visible static UI copy uses centralized i18n resources
All non-diagnostic user-visible frontend copy MUST come from centralized i18n resources instead of hardcoded strings.

#### Scenario: Main pages render localized UI copy
- **WHEN** the user visits Dashboard, Settings, History, Processing, Preview, Login, or Profile
- **THEN** titles, buttons, descriptions, empty states, Toast copy, and accessibility text MUST be resolved from locale resources
- **AND** changing the active UI language MUST update those strings consistently

### Requirement: Task progress UI is driven by structured task metadata
Frontend task progress and status views MUST use structured task metadata instead of parsing backend natural-language messages.

#### Scenario: Processing and batch views render task status
- **WHEN** the frontend receives task updates
- **THEN** Processing and batch translation views MUST derive visible status text from structured fields such as `status`, `stage`, `detail_code`, `detail_params`, and `failure_reason_code`
- **AND** the UI MUST NOT depend on `message.includes(...)` or equivalent natural-language parsing for primary task state rendering

### Requirement: Shared shell supports persistent day and dark themes
The frontend SHALL provide a shared theme preference for the application shell so users can switch between a bright daytime interface and the existing dark presentation.

#### Scenario: Default shell keeps the current dark presentation
- **WHEN** a user opens the frontend without a previously saved theme preference
- **THEN** the shared shell SHALL render with the current dark visual system by default
- **AND** the default SHALL preserve the existing dark-first information hierarchy.

#### Scenario: User switches the shell theme
- **WHEN** a user activates the shared theme toggle from the shell header
- **THEN** the frontend SHALL switch between `dark` and `light` themes without a full page reload
- **AND** the toggle copy and icon treatment SHALL remain accessible in both modes.

#### Scenario: Theme preference persists across navigation
- **WHEN** a user selects either day or dark mode
- **THEN** the frontend SHALL persist that preference for later visits
- **AND** navigating between `/`, `/paper/:paperId`, `/translate`, and other shared-shell routes SHALL keep the selected theme active.

### Requirement: Shared shell prioritizes community and minimizes operational complexity
The frontend shared shell SHALL foreground the community reading flow and minimize the need for users to think in terms of separate operational modes or tool surfaces.

#### Scenario: Community is the primary shell destination
- **WHEN** a user enters the authenticated/shared frontend shell
- **THEN** the shell SHALL make the community homepage the primary first-level destination
- **AND** the legacy translation-oriented pages SHALL remain available through a secondary tools entry rather than competing equally with the community shell.

#### Scenario: Shared shell uses a compact navigation rail
- **WHEN** the shared shell renders on desktop
- **THEN** the left navigation SHALL behave like a compact research rail rather than a wide dashboard sidebar
- **AND** the main content canvas SHALL remain visually dominant.

#### Scenario: Sidebar and canvas remain spatially coordinated
- **WHEN** the shared shell renders the community layout
- **THEN** the sidebar SHALL reserve space with visible labels instead of collapsing into an unlabeled icon strip
- **AND** the main content SHALL not be visually overlapped or cramped by the navigation rail.

#### Scenario: Agent shell preserves per-user conversation history
- **WHEN** an authenticated user uses the agent workspace
- **THEN** the shared shell SHALL preserve access to saved conversations for that user
- **AND** creating a new chat SHALL remain lightweight and not reset the overall shell structure.

#### Scenario: Tools hub preserves the old direct translation workflow
- **WHEN** a user opens the tools hub
- **THEN** the translation tool SHALL still expose the old direct translation workflow as a first-class utility
- **AND** community-first navigation SHALL not erase that explicit tool path.

### Requirement: Community conversation UI renders natural assistant chat output
The community conversation workspace SHALL render assistant runs as normal chat messages instead of reconstructing hard-coded summary cards from structured section headings, and it SHALL preserve that chat-bubble shape during live streaming.

#### Scenario: Assistant turn contains a natural-language reply
- **WHEN** the conversation page renders an assistant turn produced by the community agent
- **THEN** it SHALL display the run’s conversational message as the assistant content body
- **AND** it SHALL NOT require section headers such as “Conclusion/Current status” or “Core points” to render that turn.

#### Scenario: Citations, tool trace, and paper actions remain visible
- **WHEN** an assistant run includes citations, tool trace entries, or a paper navigation action
- **THEN** the conversation workspace SHALL continue to render those affordances alongside the conversational answer
- **AND** the UI SHALL keep the assistant answer in chat form rather than decomposing it into summary cards.

#### Scenario: Streaming answer keeps the same chat-body presentation
- **WHEN** the assistant answer is still arriving over the live stream
- **THEN** the UI SHALL keep rendering the partial answer inside the normal assistant chat bubble
- **AND** it SHALL NOT fall back to synthetic running summary cards.

### Requirement: Community conversation UI renders authenticated live streaming output
The community conversation workspace SHALL consume the authenticated live agent stream and incrementally render assistant output as the run progresses.

#### Scenario: Running assistant turn is updated incrementally
- **WHEN** the user submits a prompt in the conversation workspace
- **THEN** the UI SHALL create a running assistant turn immediately
- **AND** it SHALL append streamed text chunks into that turn without waiting for full completion.

### Requirement: Tool, citation, and action metadata hydrate during the stream
The community conversation workspace SHALL incrementally hydrate tool lifecycle, citations, and paper actions while the assistant answer is still streaming.

#### Scenario: Stream emits tool and citation events
- **WHEN** the runtime emits tool lifecycle, citation, or action events
- **THEN** the UI SHALL update the visible assistant turn metadata incrementally
- **AND** it SHALL preserve those artifacts in the final saved turn.

### Requirement: Background translation status stays inline with the answer
The community conversation workspace SHALL present translation startup as inline assistant metadata instead of replacing the answer body with a terminal placeholder.

#### Scenario: Translation is started during the answer
- **WHEN** the stream includes a translation handoff event or action
- **THEN** the UI SHALL surface it as inline assistant status or progress metadata
- **AND** it SHALL NOT replace the answer body with a terminal “translation started” placeholder.

### Requirement: Workspace sidebar is collapsed by default with an inline trigger
The application workspace SHALL set the sidebar to a collapsed state by default to maximize initial reading and conversation space, and the `SidebarTrigger` SHALL be located within the sidebar header instead of the global top navigation bar.

#### Scenario: User opens the workspace
- **WHEN** the user navigates to the community paper conversation or detail page
- **THEN** the sidebar SHALL be collapsed by default (`defaultOpen={false}`)
- **AND** the open/close trigger SHALL be visible at the top of the collapsed/expanded sidebar.

### Requirement: Inline paper reader provides maximized vertical space
The inline paper reader in the conversation workspace SHALL provide sufficient vertical space to ensure comfortable reading of complex HTML papers while allowing the overall page to remain scrollable.

#### Scenario: Reader panel height
- **WHEN** the community paper workspace renders the inline HTML reader
- **THEN** its height SHALL be optimized (e.g., `h-[calc(140dvh-160px)]`) to be larger than a single viewport, encouraging immersive reading without breaking overall page layout.

### Requirement: Community UI exposes deep research as a distinct mode
The community UI SHALL expose deep research as a distinct user-selectable mode so users can request broad literature synthesis without confusing that path with default chat.

#### Scenario: User chooses between chat and deep research
- **WHEN** the user prepares a community agent request
- **THEN** the UI SHALL expose an explicit deep research entry or mode switch
- **AND** the default chat path SHALL remain visually distinct.

### Requirement: Community UI renders long-form cited research reports
The community UI SHALL render deep research output as a report-length cited artifact rather than a short chat bubble only.

#### Scenario: Deep research report is displayed
- **WHEN** a deep research run completes
- **THEN** the UI SHALL render the result as a long-form structured report with citations
- **AND** the report SHALL remain readable without flattening all sections into one undifferentiated paragraph.

### Requirement: Community UI distinguishes deep-research progress from completion
The community UI SHALL treat deep-research progress as provisional and only present a finalized research report once a completion snapshot includes the report payload.

#### Scenario: Progress events arrive before completion
- **WHEN** a deep research run is still in progress and only non-complete stream events have arrived
- **THEN** the UI SHALL keep showing an in-progress state
- **AND** it SHALL not present the finalized deep research report card until a completed snapshot with report content is received.

### Requirement: Paper detail uses a coordinated dual-pane copilot workspace
The web UI SHALL present paper detail as a coordinated dual-pane workspace with a reading-dominant pane and a persistent paper-scoped copilot pane.

#### Scenario: Desktop paper detail keeps both panes visible
- **WHEN** the user opens the paper detail page on a desktop-width viewport
- **THEN** the reader SHALL remain the dominant pane
- **AND** the copilot pane SHALL stay visible without visually displacing the reader from its primary role.

#### Scenario: Narrow screens keep reading continuity
- **WHEN** the user opens the paper detail page on a narrower viewport
- **THEN** the UI SHALL preserve access to both reading and copilot functions
- **AND** it SHALL do so with an explicit responsive behavior instead of collapsing into an unusable cramped layout.

### Requirement: Reader and copilot interactions stay synchronized
The web UI SHALL keep active anchor, reader mode, and paper-scoped copilot metadata synchronized inside the dual-pane workspace.

#### Scenario: Citation click highlights the corresponding reader block
- **WHEN** the user clicks a copilot citation or anchor-aware action
- **THEN** the reader SHALL scroll to the target block
- **AND** the target block SHALL receive visible focus or highlight feedback.

#### Scenario: URL hash deep-link resolves after asynchronous preview rendering
- **WHEN** the user opens paper detail with a URL hash anchor whose target appears after asynchronous preview rendering/enhancement
- **THEN** the reader SHALL retry anchor activation until that target is available within bounded time
- **AND** the resolved target SHALL be scrolled into view and visibly highlighted without requiring a second user action.

#### Scenario: Translation upgrade does not reset the copilot
- **WHEN** the paper switches from source-first reading to translated reading
- **THEN** the copilot pane SHALL stay mounted with its current context
- **AND** the user SHALL not lose the active paper-scoped assistant conversation.

### Requirement: Paper-detail copilot supports true multi-turn chat with reader selection context
The web UI SHALL let users run a real multi-turn paper-scoped conversation inside paper detail, and SHALL include highlighted reader selection context in copilot runs.

#### Scenario: User highlights a reader passage and asks a follow-up question
- **WHEN** the user highlights a passage in the reader pane and sends a copilot question from the detail-side composer
- **THEN** the run payload SHALL include structured `reader_selection` context (`text`, optional `anchor_id`, and reader `mode`)
- **AND** the copilot response SHALL render in the same right-pane conversation thread without route changes.

#### Scenario: Highlighted selection remains visually discoverable while chatting
- **WHEN** the user highlights reader text and then moves focus to the copilot input to ask questions
- **THEN** the reader pane SHALL keep a visible highlight marker for the active selected passage
- **AND** clearing the selection context from the composer SHALL remove that reader highlight marker.

#### Scenario: Paper-detail chat keeps conversation memory within the same paper
- **WHEN** the user asks a second question in the same paper detail copilot thread
- **THEN** the next run SHALL include prior user/assistant turns as history context
- **AND** the thread SHALL continue rendering as one continuous in-pane conversation.

#### Scenario: Copilot composer stays visible and actionable in the right pane
- **WHEN** the paper detail workspace renders with tall reader content or long articles
- **THEN** the right-pane copilot composer (input plus run controls) SHALL remain visibly discoverable without requiring users to hunt through unrelated static filler content
- **AND** the default empty state SHALL prioritize direct chat entry over large decorative description or asset cards.


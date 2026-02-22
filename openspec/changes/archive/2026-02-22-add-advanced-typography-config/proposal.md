# Change: 添加高级排版配置与导言区注入系统

## Why
用户反馈：翻译后的 PDF 缺乏对中文阅读习惯（行距、字体、单栏、引用格式）的适配能力。当前系统仅处理语言级的字体/宏包注入（`add_cjk_package`），未提供排版层面的可配置能力。需要一个系统级"导言区注入"机制，让用户在翻译前选择排版偏好，系统自动修改 LaTeX Preamble 以适配目标格式。环境使用 TexLive 2025，所有宏包（含 gbt7714、中文字体等）均已可用。

## What Changes
- **新增 `FormattingConfig` 数据模型**：行距/字号为自定义数值输入，栏模式支持单双双向切换
- **扩展 `AdvancedConfig`**：新增 `formatting` 可选字段
- **新增 `apply_formatting_config()` 函数**：导言区正则注入逻辑
- **修改翻译流程**：`add_cjk_package()` 之后追加 `apply_formatting_config()`（包含针对 `xeCJK`/`ctex` 位置依赖的 `_inject_after_cjk_package` 专门修复）
- **扩展 `compute_config_hash()`**：纳入排版配置
- **前端排版面板**：行距/字号为启用按钮+数字输入框，其余为下拉/开关
- **完整配置集成**：复用现有 settings API、Dashboard 默认值、翻译提交、历史快照（在 `translation_tasks` 扩展独立的 `formatting` JSONB 字段直供查询）、config_hash 全链路
- **历史快照展示**：在前端 History 页面详情中反序列化并展示历史排版快照

## Impact
- Affected specs: `latex-translation-core`, `web-ui`, `user-settings`, `translation-history`
- Affected code:
  - `backend/app/models/config_models.py` - 新增 FormattingConfig
  - `backend/app/services/latex/utils.py` - 新增 apply_formatting_config()
  - `backend/app/services/agents/coordinator_agent.py` - 传递 formatting config
  - `backend/app/api/routes/translate.py` - 扩展 config_hash、传递配置
  - `backend/app/api/routes/settings.py` - 扩展 UserSettingsResponse/Update
  - `backend/app/api/routes/history.py` - 扩展 TaskHistoryItem/TaskDetailResponse 支持 formatting
  - `backend/app/services/task_manager.py` - 提取 formatting 以 JSONB 存入 DB 列
  - `frontend/src/pages/Dashboard.tsx` - 集成排版面板
  - `frontend/src/pages/History.tsx` - 历史详情面板增加排版配置快照展示
  - `frontend/src/components/FormattingPanel.tsx` - 新组件

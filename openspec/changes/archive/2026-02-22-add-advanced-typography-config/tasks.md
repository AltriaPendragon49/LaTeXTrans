## Milestone 1: 后端数据模型与导言区注入引擎

- [x] 1.1 在 `backend/app/models/config_models.py` 中新增 `FormattingConfig` Pydantic 模型
- [x] 1.2 在 `AdvancedConfig` 中添加 `formatting: Optional[FormattingConfig] = None` 字段
- [x] 1.3 在 `backend/app/services/latex/utils.py` 中实现 `apply_formatting_config()` 函数
  - 行距注入（setspace，支持任意数值）
  - 字号替换（\documentclass 选项正则，支持任意数值如 12pt）
  - 栏模式双向切换（单→双、双→单）
  - 页边距注入（geometry）
  - 首行缩进（\parindent）
  - CJK 字体覆盖（\setCJKmainfont）
  - 图表标题本地化（\renewcommand）
  - 参考文献格式替换（\bibliographystyle）
  - 引文标记风格（natbib）
- [x] 1.4 在 `apply_formatting_config()` 中添加宏包冲突检测（避免重复注入）
- [x] 1.5 新增 `_inject_after_cjk_package` 辅助函数解决 `\setCJKmainfont` 必须位于 `xeCJK` 或 `ctex` 之后的时序依赖 Bug

## Milestone 2: 翻译流程集成与配置链路

- [x] 2.1 修改 `translate.py` 中的 `run_translation()`，在 `agent_config` 中传递 `formatting` 配置
- [x] 2.2 修改 `CoordinatorAgent` 或 `GeneratorAgent`，在编译前调用 `apply_formatting_config()`
- [x] 2.3 扩展 `compute_config_hash()` 函数，将 `formatting` 配置纳入签名计算
- [x] 2.4 验证 `advanced_config` JSONB 快照自动包含 `formatting`（已嵌套在 AdvancedConfig 中）
- [x] 2.5 在 `task_manager.py` 中分离出 `formatting` 字段，并作为独立的 JSONB 列持久化到 `translation_tasks`，修复历史查询无法获取 formatting 的问题

## Milestone 3: 用户设置持久化

- [x] 3.1 在 Supabase `user_settings` 表中添加 `default_formatting` JSONB 列
- [x] 3.2 在 `settings.py` 的 `UserSettingsResponse` 中添加 `default_formatting` 字段
- [x] 3.3 在 `UserSettingsUpdate` 中添加 `default_formatting` 字段
- [x] 3.4 在 `SYSTEM_DEFAULTS` 中添加 `default_formatting: null`
- [x] 3.5 修改 `_build_response()` 和 `update_user_settings()` 处理 formatting 字段

## Milestone 4: 前端排版配置面板

- [x] 4.1 新建 `FormattingPanel.tsx` 排版配置组件
  - 行距：启用按钮 + 数字输入框（如 1.5）
  - 字号：启用按钮 + 数字输入框（如 12）
  - 字体下拉（保持原样/宋体/黑体），仅中文目标语言时显示
  - 栏模式下拉（保持原样/单栏/双栏）
  - 页边距下拉（保持原样/窄/正常/宽）
  - 段落缩进开关
  - 引用格式下拉（保持原样/国标GB/T 7714-数字/国标GB/T 7714-著者-年/IEEE/APA）
  - 引文风格下拉（保持原样/[1]数字/上标/著者-年份）
  - 标题本地化开关
- [x] 4.2 在 `Dashboard.tsx` Advanced Settings 中集成 FormattingPanel（通过 AdvancedConfig.tsx）
- [x] 4.3 Dashboard 初始化时从 `GET /api/settings` 加载 `default_formatting` 填充面板
- [x] 4.4 提交翻译时将面板状态序列化到 `advanced_config.formatting`
- [x] 4.5 在系统设置页面（Settings）中添加排版默认值配置区域
- [x] 4.6 历史页面：在 `api/routes/history.py` 中扩展 `TaskHistoryItem` 和 SQL 查询以返回 JSONB，并在 `History.tsx` 中将其展示为快照 Badge

## Milestone 5: 验证与测试

- [x] 5.1 编写 `apply_formatting_config()` 的单元测试（17 passed ✓）
  - 行距注入（自定义数值）
  - 字号替换（自定义数值）
  - 栏模式双向切换
  - 参考文献格式替换
  - 宏包冲突检测
  - None 配置不修改
- [x] 5.2 端到端验证：配置排版选项后翻译 arXiv 论文，检查 PDF 输出
- [x] 5.3 验证 config_hash：相同排版配置命中缓存，不同配置不命中
- [x] 5.4 验证历史记录快照中包含 formatting 配置，且前端 UI 展示无误
- [x] 5.5 验证系统设置 → Dashboard 默认值加载 → 翻译提交的完整链路


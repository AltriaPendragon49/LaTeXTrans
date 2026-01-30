# advanced-config Specification Delta

## Purpose
增强翻译任务的高级配置能力，使配置项真实影响翻译行为。

## ADDED Requirements

### Requirement: Advanced Configuration Panel
前端 SHALL 在新建翻译页面提供完整的高级配置面板。

#### Scenario: 展开高级配置面板
- **WHEN** 用户点击 "Advanced Settings" 展开按钮
- **THEN** 系统显示所有高级配置选项
- **AND** 所有选项显示当前值（默认或用户修改后的值）

#### Scenario: 配置翻译模式
- **WHEN** 用户选择翻译模式（全文/摘要/术语优先）
- **THEN** 选择立即生效，存储在前端状态中
- **AND** 提交翻译时该配置传递给后端

#### Scenario: 配置编译策略
- **WHEN** 用户选择编译策略（pdflatex/xelatex/自动选择）
- **THEN** 选择立即生效，存储在前端状态中
- **AND** 后端使用指定的编译器或自动选择

#### Scenario: 切换验证代理
- **WHEN** 用户切换"启用验证代理"开关
- **THEN** 开关状态立即更新
- **AND** 翻译时根据配置决定是否使用双模型验证

#### Scenario: 配置双语输出
- **WHEN** 用户启用"生成双语 PDF"选项
- **THEN** 翻译结果包含原文和译文对照

#### Scenario: 选择作者友情 API
- **WHEN** 用户保持"使用作者 API"选项为默认（开启）
- **THEN** 系统使用预配置的 API 密钥和端点
- **AND** 自定义 API 配置输入框禁用

#### Scenario: 配置自定义 API
- **WHEN** 用户关闭"使用作者 API"选项
- **THEN** 系统显示自定义 API 配置输入框
- **AND** 用户可输入中转站地址（如 https://aicanapi.com）
- **AND** 用户可输入自定义 API Key
- **AND** UI 提示"只需输入中转站地址，系统自动追加 /v1/chat/completions"

### Requirement: Default Configuration
所有高级配置项 SHALL 具有合理的默认值，访客用户无需配置即可翻译。

#### Scenario: 使用默认配置翻译
- **WHEN** 用户不修改任何高级配置
- **THEN** 系统使用默认值：
  - source_language = "en"
  - target_language = "zh"
  - translation_mode = "full"
  - compile_strategy = "auto"
  - enable_verification = true
  - bilingual_output = false
  - use_author_api = true（使用作者友情提供的 API）
- **AND** 翻译按钮始终可用
- **AND** 翻译流程正常执行

#### Scenario: 部分配置自定义
- **WHEN** 用户仅修改部分配置项（如只改目标语言）
- **THEN** 未修改的配置保持默认值
- **AND** 翻译按钮始终可用

#### Scenario: 自定义 API 未完成配置
- **WHEN** 用户关闭"使用作者 API"但未填写自定义配置
- **THEN** 系统显示警告提示"请填写中转站地址和 API Key"
- **AND** 翻译按钮仍然可用
- **AND** 点击翻译时自动回退到作者 API

### Requirement: Configuration Injection
后端 SHALL 将高级配置参数注入到翻译 Agent 中。

#### Scenario: 翻译请求包含高级配置
- **WHEN** 前端提交翻译请求
- **THEN** 请求体包含 `advanced_config` 对象
- **AND** 包含所有配置项：translation_mode, compile_strategy, enable_verification, bilingual_output, use_author_api, custom_base_url, custom_api_key

#### Scenario: 后端处理 API 配置
- **WHEN** 后端接收到 use_author_api = false 的请求
- **THEN** 后端使用 custom_base_url 和 custom_api_key 构建 LLM 配置
- **AND** 自动在 custom_base_url 末尾追加 /v1/chat/completions（如未包含）

#### Scenario: Agent 接收配置
- **WHEN** 后端创建 CoordinatorAgent
- **THEN** agent_config 包含所有高级配置映射值
- **AND** Agent 根据配置执行相应行为

### Requirement: Session-Only Configuration
高级配置 SHALL 仅在当前会话有效，刷新页面后重置。

#### Scenario: 页面刷新重置配置
- **WHEN** 用户刷新页面或关闭后重新打开
- **THEN** 所有高级配置恢复为默认值

#### Scenario: 任务保留创建时配置
- **WHEN** 任务创建成功
- **THEN** 任务记录中保存创建时的配置快照
- **AND** 查询任务详情时返回该配置

## Cross-References
- 关联: web-ui (Dashboard 页面)
- 关联: web-api (翻译接口)
- 关联: latex-translation-core (Agent 配置)

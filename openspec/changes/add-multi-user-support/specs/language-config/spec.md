# language-config Specification Delta

## Purpose
增强语言参数配置能力，使语言设置作为一等公民贯穿整个翻译流程。

## MODIFIED Requirements

### Requirement: Translation Task Initiation (from web-api)
系统 SHALL 在创建翻译任务时持久化语言配置，并将其传递给 Agent。

#### Scenario: 创建任务时保存语言配置
- **WHEN** 用户提交翻译请求，指定 source_language 和 target_language
- **THEN** 系统在 Supabase `translation_tasks` 表中存储语言配置
- **AND** 该配置在后续翻译流程中被读取和使用

#### Scenario: 使用默认语言
- **WHEN** 用户提交翻译请求但未显式指定语言
- **THEN** 系统从用户设置中读取默认语言
- **AND** 使用默认语言创建任务

#### Scenario: 语言参数传递到 Agent
- **WHEN** 翻译任务开始执行
- **THEN** 系统从任务记录中读取 source_language 和 target_language
- **AND** 将语言参数注入到 CoordinatorAgent 配置中
- **AND** Agent 不硬编码语言设置

## ADDED Requirements

### Requirement: Language Selection UI
前端 SHALL 在新建翻译页面提供语言选择 UI。

#### Scenario: 选择翻译语言
- **WHEN** 用户在新建翻译页面
- **THEN** 系统显示源语言和目标语言下拉选择器
- **AND** 默认值来自用户设置

#### Scenario: 提交翻译请求
- **WHEN** 用户点击翻译按钮
- **THEN** 请求包含用户选择的 source_language 和 target_language

## Cross-References
- 依赖: user-settings (默认语言)
- 修改: web-api (任务创建)
- 关联: web-ui (翻译配置)

# language-config Specification

## Purpose
TBD - created by archiving change add-multi-user-support. Update Purpose after archive.
## Requirements
### Requirement: Translation Task Language Persistence

The system SHALL ensure default model names are consistent across components and rely exclusively on `.env` environment variables.

#### Scenario: 确保默认模型名跨组件一致性
- **GIVEN** the system default model is `qwen/qwen3-235b-a22b`
- **THEN** both frontend fallback values (in store) and backend defaults (in Config models) MUST be identical
- **AND** all sensitive configurations (API keys, URLs) MUST exclusively rely on `.env` environment variables
- **AND** the system SHALL NOT provide hardcoded fallback keys in the code if environment variables are missing

### Requirement: Language Selection UI
前端 SHALL 在新建翻译页面提供语言选择 UI。

#### Scenario: 选择翻译语言
- **WHEN** 用户在新建翻译页面
- **THEN** 系统显示源语言和目标语言下拉选择器
- **AND** 默认值来自用户设置

#### Scenario: 提交翻译请求
- **WHEN** 用户点击翻译按钮
- **THEN** 请求包含用户选择的 source_language 和 target_language


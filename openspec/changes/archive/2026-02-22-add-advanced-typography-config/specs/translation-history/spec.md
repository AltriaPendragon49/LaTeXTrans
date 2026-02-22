## MODIFIED Requirements

### Requirement: Config Hash Storage
系统 SHALL 在 translation_tasks 表中存储翻译配置签名用于快速匹配，签名包含排版配置。

#### Scenario: 创建任务时生成 config_hash
- **WHEN** 翻译任务创建或翻译配置确定时
- **THEN** 系统计算 config_hash 并存储到 translation_tasks 表
- **AND** config_hash 基于 arxiv_id、source_language、target_language、translation_mode、compile_strategy、enable_verification、formatting 生成

#### Scenario: 排版配置影响 config_hash
- **WHEN** 两个翻译任务的排版配置不同但其他配置相同
- **THEN** 两者的 config_hash 不同
- **AND** output reuse 不会跨排版配置误命中

#### Scenario: 历史记录展示排版快照
- **WHEN** 用户在前端阅读某条历史记录详情
- **AND** 当前任务具备有效的 formatting 排版字段快照数据
- **THEN** 系统展示对应的“排版设置”区域详情
- **AND** 以具有明显视觉区分度的组件样式（如 Badge）展示其各项排版的历史选择值

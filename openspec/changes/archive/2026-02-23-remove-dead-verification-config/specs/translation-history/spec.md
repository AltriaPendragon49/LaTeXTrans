# translation-history Specification Delta

## MODIFIED Requirements

### Requirement: Translation Output Reuse
系统 SHALL 在启动翻译前检查是否有配置一致的已完成翻译可复用。

#### Scenario: 完全匹配配置时复用 output
- **WHEN** 用户启动翻译任务
- **AND** 存在已完成任务具有相同 arxiv_id、source_language、target_language、translation_mode、compile_strategy
- **THEN** 系统深拷贝已有 output 目录到新任务
- **AND** 新任务标记为 completed，跳过翻译流程
- **AND** 新任务 output 与源 output 目录独立（深拷贝）

### Requirement: Config Hash Storage
系统 SHALL 在 translation_tasks 表中存储翻译配置签名用于快速匹配，签名包含排版配置。

#### Scenario: 创建任务时生成 config_hash
- **WHEN** 翻译任务创建或翻译配置确定时
- **THEN** 系统计算 config_hash 并存储到 translation_tasks 表
- **AND** config_hash 基于 arxiv_id、source_language、target_language、translation_mode、compile_strategy、formatting 生成

## REMOVED Requirements

（无整体移除的 requirement，仅修改了上述两个场景中的字段列表，删除了 `enable_verification`）

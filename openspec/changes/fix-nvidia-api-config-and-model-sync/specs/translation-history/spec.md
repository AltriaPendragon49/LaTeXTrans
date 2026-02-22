# translation-history Spec Delta

## MODIFIED Requirements

### Requirement: Task Metadata Persistence

#### Scenario: 任务执行时同步实际使用的模型
- **GIVEN** a translation task is started with a generic `translation_model` (e.g., default placeholder)
- **WHEN** the backend determines the actual LLM config via `build_llm_config()`
- **THEN** it MUST compare the actual model name with the one in metadata
- **AND** if different, UPDATE the metadata in database to reflect the ACTUAL model used
- **AND** ensure the history record displays the actual model name (e.g., `qwen/qwen3-235b-a22b`)

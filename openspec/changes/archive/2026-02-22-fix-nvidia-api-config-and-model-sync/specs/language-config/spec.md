# language-config Spec Delta

## MODIFIED Requirements

### Requirement: Translation Task Language Persistence

The system SHALL ensure default model names are consistent across components and rely exclusively on `.env` environment variables.

#### Scenario: 确保默认模型名跨组件一致性
- **GIVEN** the system default model is `qwen/qwen3-235b-a22b`
- **THEN** both frontend fallback values (in store) and backend defaults (in Config models) MUST be identical
- **AND** all sensitive configurations (API keys, URLs) MUST exclusively rely on `.env` environment variables
- **AND** the system SHALL NOT provide hardcoded fallback keys in the code if environment variables are missing

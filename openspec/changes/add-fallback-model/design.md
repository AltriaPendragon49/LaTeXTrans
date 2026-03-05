# Architectural Design: Fallback Model Configuration

## Component Boundaries
- **Frontend Settings:** Introduce `fallback_model` in the advanced configuration UI and state management store.
- **Backend Models:** Update `AdvancedConfig` in `config_models.py` to include `fallback_model`. Update database schema or JSONB handling to persist this field.
- **Agent Orchestration:** In agents (e.g. `TranslatorAgent`), when a translation chunk retry is triggered (`attempt > 1`) or a Type C1 structural error triggers an LLM retry in the LangGraph coordinator, the agent switches from the default `model` to the configured `fallback_model` using the same `base_url` and API key.

## Trade-offs
- **Single Gateway Constraint:** Constraining the fallback model to the same API gateway simplifies credential management (no need to specify or manage a secondary API key and base URL). The trade-off is that if the provider itself is down, both models will fail, but this meets current user requirements for simplicity and targeted LLM weakness mitigation.

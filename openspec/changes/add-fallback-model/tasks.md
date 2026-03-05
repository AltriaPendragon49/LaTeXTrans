# Implementation Tasks

- [ ] Update frontend `AdvancedConfig` interfaces and `DEFAULT_ADVANCED_CONFIG` to include `fallback_model`.
- [ ] Update frontend advanced settings UI to allow users to input `fallback_model` (e.g., defaulting to `meta/llama-3.3-70b-instruct`).
- [ ] Update `.env` to define a default `LLM_FALLBACK_MODEL`.
- [ ] Update backend `AdvancedConfig` in `config_models.py` to include `fallback_model` mapped from the `.env` default.
- [ ] Modify backend `translate.py` to ensure `fallback_llm_config` is passed alongside `llm_config` to the LangGraph application, referencing the same base URL and API keys.
- [ ] Update `translator_agent.py` so that chunks retried on failures (e.g., timeout, JSON parse errors) use the `fallback_llm_config`.
- [ ] Add unit tests verifying the model switch routing during retry scenarios.

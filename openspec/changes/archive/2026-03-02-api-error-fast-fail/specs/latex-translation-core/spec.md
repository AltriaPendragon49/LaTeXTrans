## ADDED Requirements

### Requirement: API Fatal Error Fast-Fail

The system MUST short-circuit arbitrary retry backoff delays immediately upon encountering deterministic client or authentication errors from the LLM provider.

#### Scenario: Encountering a 404 or 401 error
- **WHEN** the `TranslatorAgent` or any sub-function calls the LLM completions API and receives an `aiohttp.ClientResponseError` with a status of 400, 401, 403, or 404
- **THEN** the system MUST NOT enter the progressive exponential backoff loop (e.g., 5s, 10s, 20s)
- **AND** it MUST immediately flag that segment as failed, log the fatal error exclusively, and return control backwards to avoid UI-blocking polling loops.
- **AND** the translation output for the failed segment drops back to text preservation or degraded returns directly.

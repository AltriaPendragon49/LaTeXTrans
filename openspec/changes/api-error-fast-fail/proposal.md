# Change: api-error-fast-fail

## Why
When generating a translation task, the backend previously prioritized historical API config (`user_api_config`) over the temporary advanced configuration override (`advanced_config.custom_api_key`), resulting in the translation agent calling the default or historical LLM endpoint (often resulting in 404). Furthermore, the `TranslatorAgent` reacted to these terminal client errors (400, 401, 403, 404) by initiating a rigid maximum of 3 recursive retries with exponential backoffs (5s, 10s, 20s), which severely delayed processing throughput and caused the UI polling to lock up unresponsively for minutes per translation failure.

## What Changes
- Advanced Configuration Priority: Reverse the fallback priority in `backend/app/api/routes/translate.py` to prioritize `advanced_config.custom_api_key` over user-level saved configurations.
- API Fatal Error Fast-Fail: Inject an immediate breakout condition in `TranslatorAgent` LLM execution wrappers to catch `aiohttp.ClientResponseError` with keys (400, 401, 403, 404), discarding the exponential backoff entirely and marking the translated part as failed gracefully.

## Impact
- Affected specs:
  - `web-api`
  - `latex-translation-core`
- Affected code:
  - `backend/app/api/routes/translate.py`
  - `backend/app/services/agents/translator_agent.py`
- Behavioral outcomes:
  - Temporary or guest mode LLM credential configurations successfully apply.
  - LLM errors stemming from incorrect credentials or missing models fast-fail immediately instead of dragging latency by >35 seconds due to blind retry loops.

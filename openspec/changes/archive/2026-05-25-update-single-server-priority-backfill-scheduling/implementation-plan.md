# Phase-1 System Token Pool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first rollout phase of the single-server scheduling change by adding a system-managed LLM token pool that spans two base URLs and five keys, supports quick failover on `429` and consecutive `503`, and leaves user-supplied credentials on the existing single-key path.

**Architecture:** Add a small shared LLM pool module that normalizes system-managed pool config, keeps per-member health state in-process, and exposes a single async request helper for chat-completion calls. Wire `translate.py` to emit either pooled system config or existing single-credential config, then migrate the main backend translation LLM callsites to the shared helper while preserving current custom-key behavior.

**Tech Stack:** Python 3.10+, FastAPI route config building, `aiohttp`, existing agent classes, pytest

---

### Task 1: Define pool config and routing boundary

**Files:**
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/api/routes/translate.py`
- Test: `backend/tests/unit/test_system_llm_token_pool.py`

- [ ] **Step 1: Write the failing settings/config tests**

```python
def test_settings_parse_system_llm_pool_groups_json():
    settings = config.Settings(
        _env_file=None,
        llm_api_key="dummy-key",
        llm_base_url="http://dummy/v1/chat/completions",
        llm_model="gpt-4o",
        llm_system_pool_groups_json='[{"base_url":"https://a.example/v1/chat/completions","api_keys":["k1","k2"]},{"base_url":"https://b.example/v1/chat/completions","api_keys":["k3","k4","k5"]}]',
    )
    groups = settings.get_llm_system_pool_groups()
    assert len(groups) == 2
    assert groups[0]["api_keys"] == ["k1", "k2"]
    assert groups[1]["api_keys"] == ["k3", "k4", "k5"]


async def test_build_llm_config_async_uses_system_pool_for_author_api(monkeypatch):
    advanced = AdvancedConfig(use_author_api=True)
    config_payload = await translate_route.build_llm_config_async(advanced, user_id=None)
    assert config_payload["pool_mode"] == "system_managed"
    assert len(config_payload["pool_members"]) == 5


async def test_build_llm_config_async_keeps_custom_user_key_single_route():
    advanced = AdvancedConfig(
        use_author_api=False,
        custom_base_url="https://custom.example",
        custom_api_key="user-key",
    )
    config_payload = await translate_route.build_llm_config_async(advanced, user_id=None)
    assert config_payload.get("pool_mode") != "system_managed"
    assert config_payload["api_key"] == "user-key"
```

- [ ] **Step 2: Run the config tests to verify they fail**

Run: `pytest backend/tests/unit/test_system_llm_token_pool.py -k "settings_parse_system_llm_pool_groups_json or build_llm_config_async" -v`

Expected: FAIL because the new settings field/helpers and pooled config shape do not exist yet.

- [ ] **Step 3: Implement minimal settings and route config support**

```python
class Settings(BaseSettings):
    llm_system_pool_groups_json: Optional[str] = Field(
        default=None,
        validation_alias="LLM_SYSTEM_POOL_GROUPS_JSON",
    )

    def get_llm_system_pool_groups(self) -> list[dict[str, Any]]:
        raw = str(self.llm_system_pool_groups_json or "").strip()
        if not raw:
            return []
        parsed = json.loads(raw)
        normalized = []
        for index, group in enumerate(parsed):
            base_url = _normalize_chat_completions_url(group.get("base_url"))
            api_keys = [str(item).strip() for item in group.get("api_keys", []) if str(item).strip()]
            if base_url and api_keys:
                normalized.append({
                    "group_id": f"group-{index}",
                    "base_url": base_url,
                    "api_keys": api_keys,
                })
        return normalized


async def build_llm_config_async(advanced_config: AdvancedConfig, user_id: str = None) -> Dict[str, Any]:
    if advanced_config.custom_api_key:
        return _build_single_credential_config(...)
    if user_id and stored_user_key:
        return _build_single_credential_config(...)
    system_members = _build_system_pool_members(settings.get_llm_system_pool_groups())
    if system_members:
        return {
            "base_url": settings.llm_base_url,
            "api_key": settings.llm_api_key,
            "model": advanced_config.translation_model,
            "timeout": settings.llm_timeout,
            "pool_mode": "system_managed",
            "pool_members": system_members,
        }
    return settings.get_llm_config()
```

- [ ] **Step 4: Re-run the config tests to verify they pass**

Run: `pytest backend/tests/unit/test_system_llm_token_pool.py -k "settings_parse_system_llm_pool_groups_json or build_llm_config_async" -v`

Expected: PASS for the settings/parser and route-config cases.

### Task 2: Add the shared pool manager and failover policy

**Files:**
- Create: `backend/app/services/agents/llm_token_pool.py`
- Test: `backend/tests/unit/test_system_llm_token_pool.py`

- [ ] **Step 1: Write the failing pool-manager tests**

```python
@pytest.mark.asyncio
async def test_pool_fails_over_to_another_member_after_429():
    pool = build_test_pool()
    session = FakeSession([
        FakeResponse(status=429, headers={"Retry-After": "0"}),
        FakeResponse(status=200, json_data={"choices": [{"message": {"content": "ok"}}]}),
    ])
    result = await post_chat_completion_with_pool(
        session=session,
        llm_config=pool,
        payload={"model": "demo", "messages": []},
        timeout=aiohttp.ClientTimeout(total=5),
    )
    assert result["choices"][0]["message"]["content"] == "ok"
    assert session.calls[0]["base_url"] != session.calls[1]["base_url"] or session.calls[0]["api_key"] != session.calls[1]["api_key"]


@pytest.mark.asyncio
async def test_pool_switches_after_consecutive_503():
    pool = build_test_pool()
    session = FakeSession([
        FakeResponse(status=503),
        FakeResponse(status=503),
        FakeResponse(status=200, json_data={"choices": [{"message": {"content": "ok"}}]}),
    ])
    result = await post_chat_completion_with_pool(...)
    assert result["choices"][0]["message"]["content"] == "ok"


@pytest.mark.asyncio
async def test_pool_sticks_to_current_member_when_all_members_exhausted(monkeypatch):
    pool = build_test_pool(single_available_member=True)
    session = FakeSession([
        FakeResponse(status=429, headers={"Retry-After": "0"}),
        FakeResponse(status=429, headers={"Retry-After": "0"}),
        FakeResponse(status=200, json_data={"choices": [{"message": {"content": "ok"}}]}),
    ])
    result = await post_chat_completion_with_pool(...)
    assert result["choices"][0]["message"]["content"] == "ok"
    assert len({call["member_id"] for call in session.calls}) == 1
```

- [ ] **Step 2: Run the pool-manager tests to verify they fail**

Run: `pytest backend/tests/unit/test_system_llm_token_pool.py -k "fails_over_to_another_member_after_429 or switches_after_consecutive_503 or sticks_to_current_member" -v`

Expected: FAIL because `llm_token_pool.py` and `post_chat_completion_with_pool()` do not exist yet.

- [ ] **Step 3: Implement the minimal pool module**

```python
@dataclass
class PoolMemberState:
    member_id: str
    base_url: str
    api_key: str
    cooldown_until: float = 0.0
    consecutive_429: int = 0
    consecutive_503: int = 0
    last_used_at: float = 0.0


async def post_chat_completion_with_pool(
    *,
    session: aiohttp.ClientSession,
    llm_config: Mapping[str, Any],
    payload: Dict[str, Any],
    timeout: aiohttp.ClientTimeout,
    on_retry_message: Optional[Callable[[str], None]] = None,
) -> Dict[str, Any]:
    if llm_config.get("pool_mode") != "system_managed":
        return await _post_once(...)

    state = _registry.ensure_pool(llm_config["pool_members"])
    current = state.select_initial_member()
    while True:
        response = await _post_once(...)
        if response.status == 429 and state.has_healthy_alternative(current.member_id):
            state.record_429(current.member_id, retry_after=response.headers.get("Retry-After"))
            current = state.select_alternative(current.member_id)
            continue
        if response.status == 503:
            state.record_503(current.member_id)
            if state.should_failover_after_503(current.member_id) and state.has_healthy_alternative(current.member_id):
                current = state.select_alternative(current.member_id)
                continue
        if response.status in (429, 503) and not state.has_healthy_alternative(current.member_id):
            await asyncio.sleep(state.sticky_retry_delay(response.status, response.headers))
            continue
        response.raise_for_status()
        result = await response.json()
        state.record_success(current.member_id)
        return result
```

- [ ] **Step 4: Re-run the pool-manager tests to verify they pass**

Run: `pytest backend/tests/unit/test_system_llm_token_pool.py -k "fails_over_to_another_member_after_429 or switches_after_consecutive_503 or sticks_to_current_member" -v`

Expected: PASS for the pool failover and sticky-retry tests.

### Task 3: Integrate the shared helper into active backend LLM calls

**Files:**
- Modify: `backend/app/services/agents/translator_agent.py`
- Modify: `backend/app/services/agents/parser_agent.py`
- Test: `backend/tests/unit/test_system_llm_token_pool.py`

- [ ] **Step 1: Write the failing integration tests**

```python
@pytest.mark.asyncio
async def test_translator_agent_main_request_uses_pool_helper_for_system_credentials(monkeypatch, tmp_path):
    agent = build_translator_with_system_pool(tmp_path)
    called = {}

    async def fake_pool_call(**kwargs):
        called["pool_mode"] = kwargs["llm_config"].get("pool_mode")
        return {"choices": [{"message": {"content": "translated"}}]}

    monkeypatch.setattr(pool_module, "post_chat_completion_with_pool", fake_pool_call)
    result = await agent._request_llm(...)
    assert result == "translated"
    assert called["pool_mode"] == "system_managed"


@pytest.mark.asyncio
async def test_custom_user_credentials_keep_existing_single_route(monkeypatch, tmp_path):
    agent = build_translator_with_custom_key(tmp_path)
    session = FakeSession([FakeResponse(status=200, json_data={"choices": [{"message": {"content": "translated"}}]})])
    result = await agent._request_llm(...)
    assert result == "translated"
    assert len(session.calls) == 1
```

- [ ] **Step 2: Run the integration tests to verify they fail**

Run: `pytest backend/tests/unit/test_system_llm_token_pool.py -k "translator_agent_main_request_uses_pool_helper or custom_user_credentials_keep_existing_single_route" -v`

Expected: FAIL because the agents still call `session.post()` directly.

- [ ] **Step 3: Implement the minimal integration**

```python
if self.config.get("llm_config", {}).get("pool_mode") == "system_managed":
    result = await post_chat_completion_with_pool(
        session=session,
        llm_config=self.config["llm_config"],
        payload=payload,
        timeout=_timeout,
        on_retry_message=_progress_callback,
    )
else:
    async with session.post(self.base_url, json=payload, headers=headers, timeout=_timeout) as response:
        ...
```

- [ ] **Step 4: Re-run the integration tests to verify they pass**

Run: `pytest backend/tests/unit/test_system_llm_token_pool.py -k "translator_agent_main_request_uses_pool_helper or custom_user_credentials_keep_existing_single_route" -v`

Expected: PASS for both the pooled system path and the preserved custom-key path.

### Task 4: Focused verification and spec sync

**Files:**
- Modify: `openspec/changes/update-single-server-priority-backfill-scheduling/tasks.md`
- Test: `backend/tests/unit/test_system_llm_token_pool.py`

- [ ] **Step 1: Run the focused phase-1 test suite**

Run: `pytest backend/tests/unit/test_system_llm_token_pool.py -v`

Expected: PASS with the new config, pool-manager, and integration coverage.

- [ ] **Step 2: Run a second focused regression slice against touched agent tests**

Run: `pytest backend/tests/unit/test_controlled_repair_agent.py backend/tests/unit/test_translation_repair_agent.py backend/tests/unit/test_step4_diagnostic_node.py -q`

Expected: PASS with no new failures introduced by shared pool integration.

- [ ] **Step 3: Re-validate the OpenSpec change**

Run: `openspec validate update-single-server-priority-backfill-scheduling --strict --no-interactive`

Expected: `Change 'update-single-server-priority-backfill-scheduling' is valid`

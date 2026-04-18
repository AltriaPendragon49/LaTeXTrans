# Structured Insight Base Failover And AST Sourcing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make structured insight generation faster and more stable by using hybrid runtime source packets, concurrent first-pass module generation, and structured-insight-local base preference on repeated `503` failures.

**Architecture:** Keep the publication gate and Chinese-only output unchanged. Extend the source builder in `paper_service.py` to emit richer section packets, add a parallel first-pass plus targeted repair loop for the five modules, and extend `llm_token_pool.py` with optional task-local base preference while preserving global member-level health semantics.

**Tech Stack:** Python 3, FastAPI service layer, aiohttp, pytest, OpenSpec

---

### Task 1: Expand Structured Insight Runtime Source Packets

**Files:**
- Modify: `backend/app/services/paper_service.py`
- Test: `backend/tests/unit/test_structured_insight_generation.py`

- [ ] **Step 1: Write the failing source-packet test**

```python
def test_load_structured_insight_runtime_sections_include_source_and_translation(monkeypatch, tmp_path):
    ...
    sections = paper_service._load_structured_insight_runtime_sections("task-1")
    assert sections[0]["source_content"]
    assert sections[0]["translated_content"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/unit/test_structured_insight_generation.py -q`
Expected: FAIL because `_load_structured_insight_runtime_sections` does not exist yet.

- [ ] **Step 3: Implement runtime section packet loader and hybrid excerpt composition**

```python
def _load_structured_insight_runtime_sections(task_id: str) -> List[Dict[str, Any]]:
    ...
    normalized_sections.append(
        {
            "index": index,
            "title": title,
            "source_content": normalized_source,
            "translated_content": normalized_translated,
        }
    )
```

- [ ] **Step 4: Update source preparation to prefer runtime hybrid packets**

```python
sources = _prepare_structured_insight_sources(task_id)
assert "source_excerpt" in sources["problem"]
assert "translated_excerpt" in sources["problem"]
```

- [ ] **Step 5: Run tests to verify the new source builder passes**

Run: `pytest backend/tests/unit/test_structured_insight_generation.py -q`
Expected: PASS for the new source-packet coverage.

### Task 2: Parallel First Pass Plus Targeted Repair

**Files:**
- Modify: `backend/app/services/paper_service.py`
- Test: `backend/tests/unit/test_structured_insight_generation.py`

- [ ] **Step 1: Write a failing concurrency-and-repair test**

```python
def test_generate_structured_insight_sections_runs_first_pass_concurrently_and_repairs_only_invalid(monkeypatch):
    ...
    assert call_counts["problem"] == 1
    assert call_counts["future"] == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/unit/test_structured_insight_generation.py -q`
Expected: FAIL because generation is still serial and does not do targeted repair after a parallel first pass.

- [ ] **Step 3: Implement a first-pass concurrent generator**

```python
first_pass = await asyncio.gather(
    *[
        _generate_single_structured_insight_section(...)
        for section_key in STRUCTURED_INSIGHT_SECTION_KEYS
    ]
)
```

- [ ] **Step 4: Add targeted repair for unreadable or duplicated modules**

```python
invalid_keys = _detect_invalid_structured_insight_sections(first_pass)
for section_key in invalid_keys:
    repaired[section_key] = await _generate_single_structured_insight_section(
        ...,
        previous_module_briefs=valid_briefs,
    )
```

- [ ] **Step 5: Re-run the structured insight unit tests**

Run: `pytest backend/tests/unit/test_structured_insight_generation.py -q`
Expected: PASS with concurrency plus incremental repair behavior covered.

### Task 3: Task-Local Base Preference And Member 503 Cooldown

**Files:**
- Modify: `backend/app/services/agents/llm_token_pool.py`
- Modify: `backend/app/services/paper_service.py`
- Test: `backend/tests/unit/test_system_llm_token_pool.py`
- Test: `backend/tests/unit/test_structured_insight_generation.py`

- [ ] **Step 1: Write failing pool tests for member cooldown and preferred-base routing**

```python
@pytest.mark.asyncio
async def test_pool_prefers_task_requested_base_when_healthy():
    ...

@pytest.mark.asyncio
async def test_pool_uses_longer_503_member_cooldown():
    ...
```

- [ ] **Step 2: Run targeted pool tests to verify failure**

Run: `pytest backend/tests/unit/test_system_llm_token_pool.py -q`
Expected: FAIL because the pool has no preferred-base hint and still uses a one-second `503` cooldown.

- [ ] **Step 3: Extend the pool helper with optional preferred-base selection**

```python
async def post_chat_completion_with_pool(..., selection_strategy=None):
    preferred_base_urls = selection_strategy.preferred_base_urls() if selection_strategy else ()
    current = _POOL_REGISTRY.choose_member(pool_id, preferred_base_urls=preferred_base_urls)
```

- [ ] **Step 4: Add structured-insight-local base tracking in `paper_service.py`**

```python
tracker = StructuredInsightBaseTracker(threshold=3)
tracker.record_retryable_status(base_url, status_code)
preferred_base_urls = tracker.preferred_base_urls()
```

- [ ] **Step 5: Re-run the focused pool and structured insight tests**

Run: `pytest backend/tests/unit/test_system_llm_token_pool.py backend/tests/unit/test_structured_insight_generation.py -q`
Expected: PASS for preferred-base routing, longer `503` cooldown, and structured-insight-local base shifting.

### Task 4: Local Verification And OpenSpec Sync

**Files:**
- Modify: `openspec/changes/update-structured-insight-base-failover-and-ast-sourcing/tasks.md`

- [ ] **Step 1: Run OpenSpec validation**

Run: `openspec validate update-structured-insight-base-failover-and-ast-sourcing --strict --no-interactive`
Expected: `Change 'update-structured-insight-base-failover-and-ast-sourcing' is valid`

- [ ] **Step 2: Run local focused tests**

Run: `pytest backend/tests/unit/test_system_llm_token_pool.py backend/tests/unit/test_structured_insight_generation.py -q`
Expected: PASS

- [ ] **Step 3: Mark completed implementation tasks honestly**

```markdown
- [x] 1.1 ...
- [x] 4.2 ...
```

- [ ] **Step 4: Confirm git diff only contains intended files**

Run: `git status --short`
Expected: only the structured insight change files, code changes, and related tests appear.

### Task 5: Server Validation Via Admin Ingestion Path

**Files:**
- No repo file change required for the validation steps themselves

- [ ] **Step 1: Push the worktree branch**

Run: `git push -u origin update-structured-insight-base-failover-and-ast-sourcing`
Expected: remote branch created or updated.

- [ ] **Step 2: Sync the exact branch onto the server in temporary validation state**

Run: `git fetch origin update-structured-insight-base-failover-and-ast-sourcing`
Expected: server can check out the test branch or reset a validation branch to that commit.

- [ ] **Step 3: Restart backend and run admin ingestion validation for `2508.18791`**

Run: use the repo’s documented admin ingestion path and inspect the resulting task logs, structured insight logs, and persisted sections.
Expected: five Chinese modules generated, reduced `503` churn, and no regression in publication gating.

- [ ] **Step 4: Realign production to canonical history after validation**

Run: after merge to `main`, sync server to `origin/main`, restart `latextrans-backend.service`, and verify health.
Expected: deployed server SHA matches canonical `main` and health checks succeed.

# Unified Placeholder Hard-Freeze Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a unified hard-freeze transport protocol for all protected placeholders/sentinels, enforce exact token-stream verification for structural-risk LLM calls, and keep downstream validation and fallback behavior intact.

**Architecture:** Add a request-local freeze manifest and transport-token encoder/decoder in LaTeX utilities, route translator LLM entrypoints through the new boundary, and surface protocol violations as explicit invalid attempts rather than speculative repairs. Existing validator, reconstruction, and compile fallback logic remains active after a response is accepted or rejected.

**Tech Stack:** Python, pytest, FastAPI backend services, translator/validator LaTeX utilities

---

### Task 1: Add failing protocol tests

**Files:**
- Modify: `backend/tests/unit/test_translator_payload_guard.py`
- Modify: `backend/tests/unit/test_hard_freeze_validator.py`
- Test: `backend/tests/unit/test_translator_payload_guard.py`
- Test: `backend/tests/unit/test_hard_freeze_validator.py`

- [ ] **Step 1: Write failing tests for hard-freeze token transport**

Add tests that assert:
- `_prepare_llm_payload_text()` replaces `PLACEHOLDER_*` families with opaque `@@HF:...@@` tokens
- `_call_llm_with_freeze()` rejects reordered, missing, duplicate, and unknown hard-freeze token streams
- protocol-rejected responses do not decode into persisted translated content

- [ ] **Step 2: Run targeted tests to verify they fail**

Run: `pytest backend/tests/unit/test_translator_payload_guard.py backend/tests/unit/test_hard_freeze_validator.py -q`
Expected: FAIL in new hard-freeze protocol tests because transport-token encoding and exact verification do not exist yet.

### Task 2: Implement request-local hard-freeze protocol

**Files:**
- Modify: `backend/app/services/latex/utils.py`
- Modify: `backend/app/services/agents/translator_agent.py`
- Test: `backend/tests/unit/test_translator_payload_guard.py`

- [ ] **Step 3: Implement hard-freeze registry and manifest helpers**

Add utility functions for:
- protected token extraction across `PLACEHOLDER_*`, `ENV_*`, `INLMATH_*`, `ITEM_*`, `EQROW_*`, `EQCOMMENT_*`, `PROTECTED_CMD_*`
- request-local opaque token generation
- exact sequence verification
- exact decode using a request-local manifest

- [ ] **Step 4: Integrate the protocol into translator freeze boundary**

Update translator payload preparation and restoration so structural-risk calls:
- encode all protected artifacts to `@@HF:...@@`
- verify raw response token stream before decode
- reject invalid attempts with typed reason instead of fuzzy boundary repair

- [ ] **Step 5: Run targeted protocol tests to verify they pass**

Run: `pytest backend/tests/unit/test_translator_payload_guard.py backend/tests/unit/test_hard_freeze_validator.py -q`
Expected: PASS for the newly added hard-freeze protocol tests.

### Task 3: Preserve orchestration compatibility and observability

**Files:**
- Modify: `backend/app/services/agents/translator_agent.py`
- Modify: `backend/app/services/agents/validator_agent.py`
- Test: `backend/tests/unit/test_translator_payload_guard.py`

- [ ] **Step 6: Wire protocol rejection into existing fallback semantics**

Ensure invalid responses:
- mark stable fallback reasons / metrics
- do not update translated content from invalid raw responses
- still flow into current retry and fallback behavior

- [ ] **Step 7: Extend tests for fallback compatibility**

Add tests that assert protocol violations become explicit invalid-attempt outcomes without breaking current translator fallback bookkeeping.

- [ ] **Step 8: Run the focused backend suite**

Run: `pytest backend/tests/unit/test_translator_payload_guard.py backend/tests/unit/test_hard_freeze_validator.py backend/tests/unit/services/latex/test_placeholders.py -q`
Expected: PASS with 0 failures.

### Task 4: End-to-end verification and branch hygiene

**Files:**
- Modify: `openspec/changes/strengthen-unified-placeholder-hard-freeze/tasks.md`

- [ ] **Step 9: Run implementation verification commands**

Run: `pytest backend/tests/unit/test_translator_payload_guard.py backend/tests/unit/test_hard_freeze_validator.py backend/tests/unit/services/latex/test_placeholders.py -q`
Expected: PASS with 0 failures.

- [ ] **Step 10: Mark completed OpenSpec tasks honestly**

Update `openspec/changes/strengthen-unified-placeholder-hard-freeze/tasks.md` to reflect completed implementation items that were actually finished in this session.

- [ ] **Step 11: Commit implementation branch changes**

Run:
`git add backend/app/services/latex/utils.py backend/app/services/agents/translator_agent.py backend/app/services/agents/validator_agent.py backend/tests/unit/test_translator_payload_guard.py backend/tests/unit/test_hard_freeze_validator.py backend/tests/unit/services/latex/test_placeholders.py openspec/changes/strengthen-unified-placeholder-hard-freeze/tasks.md openspec/changes/strengthen-unified-placeholder-hard-freeze/implementation-plan.md`

Then:
`git commit -m "feat: harden unified placeholder freeze protocol"`

- [ ] **Step 12: Deploy and translate regression paper 2210.03629**

Follow:
- `texts/云部署与运维/访问与登录/服务器、登录相关文档.md`
- `texts/云部署与运维/云部署运维指南.md`

Then run a real translation regression for arXiv `2210.03629` and confirm the task completes without placeholder-corruption regressions.

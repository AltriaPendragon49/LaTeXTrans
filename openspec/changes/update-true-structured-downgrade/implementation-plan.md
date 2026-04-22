# True Structured Downgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Relax section-level hard-freeze to preserve stable translated prose while making structured downgrade succeed only on real target-language output.

**Architecture:** Keep the existing hard-freeze transport protocol, but split accepted verification into strict high-risk anchors and relaxed section-like prose tokens. Then tighten deterministic downgrade/orchestration paths so successful downgrade always renders materially translated target-language text and never blesses source-English or fixed boilerplate fallback.

**Tech Stack:** Python 3, pytest, OpenSpec, existing translator/langgraph/LaTeX utility modules

---

### Task 1: Lock The Spec

**Files:**
- Modify: `openspec/changes/update-true-structured-downgrade/proposal.md`
- Modify: `openspec/changes/update-true-structured-downgrade/design.md`
- Modify: `openspec/changes/update-true-structured-downgrade/tasks.md`
- Create: `openspec/changes/update-true-structured-downgrade/specs/latex-translation-core/spec.md`
- Create: `openspec/changes/update-true-structured-downgrade/specs/hard-freeze/spec.md`
- Create: `openspec/changes/update-true-structured-downgrade/specs/translation-orchestration/spec.md`

- [ ] Step 1: Write the spec deltas
- [ ] Step 2: Run `openspec validate update-true-structured-downgrade --strict --no-interactive`
- [ ] Step 3: Fix any validation issues before touching code

### Task 2: Write Failing Hard-Freeze Tests

**Files:**
- Modify: `backend/tests/unit/test_generator_structure_guard_regressions.py`
- Create or Modify: `backend/tests/unit/test_hard_freeze_risk_tiering.py`

- [ ] Step 1: Add tests that accept section-like outputs with preserved high-risk anchors but reordered low-risk protected tokens
- [ ] Step 2: Run the focused pytest selection and confirm the new tests fail for the expected reason
- [ ] Step 3: Add tests that still fail on missing, duplicated, or reordered high-risk anchors

### Task 3: Write Failing Downgrade Tests

**Files:**
- Create or Modify: `backend/tests/unit/test_true_structured_downgrade.py`

- [ ] Step 1: Add tests proving deterministic downgrade accepts real Chinese text and rejects source-English or repeated boilerplate fallback text as successful downgrade content
- [ ] Step 2: Run the focused pytest selection and confirm the tests fail for the expected reason

### Task 4: Implement Risk-Tiered Hard-Freeze

**Files:**
- Modify: `backend/app/services/latex/utils.py`
- Modify: `backend/app/services/agents/translator_agent.py`

- [ ] Step 1: Add helper logic that classifies hard-freeze tokens by risk tier and verification mode
- [ ] Step 2: Thread relaxed verification through section-like prose translation paths only
- [ ] Step 3: Preserve strict verification for env/list/math/caption ownership anchors
- [ ] Step 4: Run the focused pytest selection and confirm hard-freeze tests now pass

### Task 5: Implement Target-Language-Only Structured Downgrade

**Files:**
- Modify: `backend/app/services/translation/ultimate_downgrade.py`
- Modify: `backend/app/services/agents/langgraph_orchestrator.py`
- Modify: `backend/app/services/agents/translator_agent.py`

- [ ] Step 1: Add downgrade eligibility checks for materially translated target-language text
- [ ] Step 2: Prevent source-English and fixed boilerplate fallback text from being recorded as successful structured downgrade
- [ ] Step 3: Run the focused pytest selection and confirm downgrade tests now pass

### Task 6: Verify And Prepare Release

**Files:**
- Modify: `openspec/changes/update-true-structured-downgrade/tasks.md`

- [ ] Step 1: Run `openspec validate update-true-structured-downgrade --strict --no-interactive`
- [ ] Step 2: Run focused backend pytest commands covering the new behavior
- [ ] Step 3: Review `git status` and the staged diff for the full workspace
- [ ] Step 4: Commit all workspace contents on the fix branch
- [ ] Step 5: Push the fix branch and deploy it on the server

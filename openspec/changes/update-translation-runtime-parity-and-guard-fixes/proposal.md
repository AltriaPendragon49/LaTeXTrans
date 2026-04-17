# Change: Update Translation Runtime Parity And Guard Fixes

## Why
Recent debugging showed two distinct problems in the current backend path. First, single-task translation throughput regressed versus the standalone CLI because backend runtime defaults and route-level parity caps reduced effective LLM concurrency from `10` to `3`. Second, two stability fixes were needed in the translation guardrail chain: `structure_guard` could misassemble `\input` trees and report false structural failures, and hard-freeze invariant failures in captions and environments could re-enter expensive retry paths instead of short-circuiting cleanly.

## What Changes
- Restore backend single-task LLM concurrency parity with the standalone CLI by raising the default backend limit and route cap from `3` to `10`.
- Preserve compile-slot safety and task-queue behavior for now; document compile serialization as a residual bottleneck rather than expanding it in this change.
- Fix project-text assembly so `\input` and `\include` content is inlined at the callsite and resolved relative to the current file directory.
- Ensure hard-freeze protocol violations for sections, captions, and environments short-circuit to explicit passthrough metadata instead of amplifying retries.
- Deduplicate failed part identifiers so repeated invariant failures do not inflate retry work.
- Add regression tests and record the implementation details for this worktree.

## Impact
- Affected specs: `latex-translation-core`, `translation-orchestration`
- Affected code: `backend/app/core/config.py`, `backend/app/api/routes/translate.py`, `backend/app/services/latex/structure_guard.py`, `backend/app/services/agents/translator_agent.py`, focused backend unit tests, and OpenSpec records

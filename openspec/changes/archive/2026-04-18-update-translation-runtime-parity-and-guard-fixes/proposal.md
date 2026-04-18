# Change: Update Translation Runtime Parity And Guard Fixes

## Why
Recent debugging showed that the current slowdown story has two different layers that must be documented separately.

The first layer is internal to this backend path and is in scope for this change:

- single-task translation throughput regressed versus the standalone CLI because backend runtime defaults and route-level parity caps reduced effective LLM concurrency from `10` to `3`;
- `structure_guard` could misassemble `\input` trees and report false structural failures;
- hard-freeze invariant failures in sections, captions, and environments could re-enter expensive retry paths instead of converging cleanly;
- plain API failures could still spill into rescue and retry bookkeeping in ways that made investigation harder.

The second layer is external to these code fixes and is not actually solved by this change:

- the live provider route can return upstream `503 Service Unavailable`;
- the backend still lacks health-aware token/provider pool behavior at the orchestration boundary;
- queue fairness, lane priority, pool cooldown, and sidecarization belong to the broader runtime/scheduling architecture rather than this narrow parity-and-guard fix.

The current proposal should therefore describe this change honestly: it fixes verified internal runtime-parity and guard-orchestration defects, and it records the residual bucket/provider problem explicitly instead of implying that local translator fixes solve provider instability.

## What Changes
- Restore backend single-task LLM concurrency parity with the standalone CLI by raising the default backend limit and route cap from `3` to `10`.
- Preserve compile-slot safety and current task-queue behavior for now; document compile serialization as a residual bottleneck rather than expanding it in this change.
- Fix project-text assembly so `\input` and `\include` content is inlined at the callsite and resolved relative to the current file directory.
- Ensure hard-freeze protocol violations for sections, captions, and environments short-circuit to explicit passthrough metadata instead of amplifying retries.
- Short-circuit rescue/retry escalation after plain API failure so transport/provider outages are not misrepresented as local placeholder-fix regressions.
- Deduplicate failed part identifiers and keep failure bookkeeping aligned with final safe states so repeated invariant failures do not inflate retry work.
- Record provider-instability findings and the boundary between this change and the broader token-pool / scheduling work.
- Cross-reference the follow-on scheduling change instead of pretending this change solves bucket health, failover, or provider availability.
- Add regression tests and record the implementation details for this worktree.

## Impact
- Affected specs: `latex-translation-core`, `translation-orchestration`
- Affected code: `backend/app/core/config.py`, `backend/app/api/routes/translate.py`, `backend/app/services/latex/structure_guard.py`, `backend/app/services/agents/translator_agent.py`, focused backend unit tests, and OpenSpec records
- Related but separate follow-up: `openspec/changes/update-single-server-priority-backfill-scheduling/`

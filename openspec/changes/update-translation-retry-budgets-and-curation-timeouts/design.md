## Context

Live production investigation showed that abnormal spend is driven less by the raw task count and more by repeated remedial LLM activity on pathological papers. The same investigation also showed that admin-curation timeout handling currently measures one 30-minute wall clock that covers download, queueing, and execution together, then cancels or abandons work in ways that can leave persisted task state inconsistent with runtime reality.

The design therefore needs to do three things together:

1. Bound rescue amplification before cost runs away.
2. Make the counting scope explicit so future changes cannot silently bypass the budget.
3. Separate queue/admission waiting from active execution timing so curation failures better reflect real work performed.

## Goals

- Reduce abnormal LLM spend without collapsing success rates for normal papers.
- Preserve useful recovery paths such as structured generation and bounded nested rescue.
- Ensure every cancellation or budget exhaustion path resolves to a deterministic terminal state.
- Keep admin-curation publication quality gates intact.
- Make fatal upstream-provider failures visible and bounded instead of letting them silently consume the rescue budget.

## Non-Goals

- This change does not remove structured insight generation from admin curation.
- This change does not redesign the translation pipeline into a new orchestration architecture.
- This change does not attempt to provision new upstream quota or automatically heal broken provider channels.

## Decisions

### Decision: Use layered remedial budgets instead of time-only stop-loss

The translation pipeline will enforce multiple ceilings rather than relying on a single wall-clock timeout:

- Local remedial retry max per callsite: `2`
- Nested rescue max per part: `4`
- Nested rescue max per task: `24`
- Total remedial LLM calls per task: `40`
- `HARD_FREEZE_PROTOCOL_VIOLATION` max per task: `8`
- Consecutive no-progress remedial attempts per task: `3`
- Outer validate/retranslate rounds: `2`

This preserves recoverability for papers with a few bad regions while stopping pathological papers from consuming unbounded rescue budget.

### Decision: Define the total remedial LLM call budget by call intent, not helper function name

The `40`-call task budget is a semantic counter. It counts any LLM invocation whose purpose is to repair or retry prior failure rather than perform a first-pass baseline step.

Count into the task remedial budget:

- nested rescue
- paragraph rescue
- masked rescue
- fragment rescue
- force retry
- validate-triggered retranslation
- repair, downgrade, or equivalent corrective re-invocations

Do not count into the task remedial budget:

- normal first-pass translation of a section/part
- non-failure-driven baseline steps required by the standard pipeline

The implementation may fan these calls through different helpers, but the counter semantics must remain tied to the intent above.

### Decision: Separate admission waiting from execution timing for admin curation

Admin curation will stop using one coarse timeout that includes download, queue, and execution together. Instead:

- Admission-stage waiting covers source download, source validation, and queue residence before active translation execution starts.
- Execution-stage timing begins only after the translation task has actually started active processing.
- Queue/admission waiting must not consume execution budget.
- Time budgets are secondary stop-losses behind retry and no-progress budgets.

This avoids failing a paper solely because it waited in line behind other work.

### Decision: Define execution-stage start with an explicit runtime boundary

Execution-stage timeout must begin from a durable runtime signal rather than inferred wall-clock heuristics. The canonical boundary is the first persisted transition that indicates active translation work has started for the translation task, not earlier curation-side enqueueing, download completion, or source validation.

Implementation may choose the exact event name, but the event must be:

- persisted,
- observable to timeout logic,
- emitted once per run before the first active remedial or first-pass translation work begins.

### Decision: Fatal upstream-provider errors are bounded and short-circuit rescue amplification

Authentication failures, quota exhaustion, unsupported-model responses, and equivalent deterministic upstream fatal errors must not be treated like recoverable structural translation failures. They should consume at most a small bounded number of failover or retry decisions and then terminate the run or route to a clearly bounded fallback path.

This does not solve quota procurement, but it prevents pathological repeated spending against a broken provider path.

### Decision: Budget exhaustion and cancellation must map to explicit terminal states

When any hard budget or timeout is exhausted:

- the current translation run must stop accepting further remedial work,
- the persisted task state must transition to a terminal failure or terminal interrupted state with machine-readable reason,
- if cleanup chooses cancellation, the live backend execution for that run must be actively terminated rather than left running in the background,
- admin-curation state must record which budget fired,
- backend status surfaces must expose the stable terminal reason or timeout reason to operators,
- the system must not leave the translation task in `processing` after runtime execution is gone.

Cancellation is therefore an all-or-nothing contract:

- either the run is allowed to continue and remains non-terminal,
- or the run is cancelled, in which case both persisted terminal state and runtime termination are mandatory.

### Decision: Admin curation disables terminology-table generation by default

Admin-curation triggered translation tasks will keep structured insight generation enabled, but they will default `generate_terminology_table=false`. This removes a lower-value spend path from intake while preserving structured outputs needed for paper quality.

## Alternatives Considered

### Keep the current time-only stop-loss

Rejected because it does not control rescue amplification early enough and it incorrectly charges queueing delay against execution time.

### Use only one global remedial-call cap

Rejected because it cannot distinguish a locally salvageable bad part from a globally pathological task. Layered caps allow bounded recovery without letting one paper monopolize the whole budget.

### Disable structured insight generation too

Rejected because product direction still values structured outputs for curated papers, and the user explicitly wants to keep this path.

## Risks / Trade-offs

- Some difficult but recoverable papers may fail earlier than before. The layered limits are chosen to tighten cost control without becoming overly aggressive.
- More counters and failure reasons increase implementation complexity, so naming and telemetry have to stay consistent.
- Separating admission and execution timing requires a reliable event boundary for “active translation started”; that boundary must be explicit in runtime state.

## Migration Plan

1. Add explicit counter definitions and terminal reasons to the translation orchestration layer.
2. Update admin-curation wait logic to use stage-aware timing and config defaults.
3. Bound fatal upstream-provider error handling and map it to stable terminal reasons.
4. Update cancellation/failure reconciliation so runtime termination and persisted task state cannot diverge.
5. Expose stable terminal reasons in task and admin-curation status surfaces.
6. Observe production metrics for average per-paper cost, timeout rate, and successful completion rate after rollout.

## Open Questions

- Whether execution-stage timeout should remain 30 minutes initially or be tightened after remedial budgets prove effective is intentionally deferred to implementation and rollout tuning.

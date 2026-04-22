## 1. Specification

- [x] 1.1 Add translation-orchestration requirements for layered remedial budgets, counting semantics, and terminal outcomes.
- [x] 1.2 Add admin-curation requirements for stage-aware timeout budgeting and curation-specific translation defaults.
- [x] 1.3 Add cancellation requirements so canceled or timed-out runs cannot remain in `processing`.
- [x] 1.4 Add web-api requirements for stable terminal-reason visibility in task and admin-curation status responses.

## 2. Implementation

- [x] 2.1 Add per-part, per-task, and consecutive-no-progress remedial counters in translation orchestration.
- [x] 2.2 Cap outer validate/retranslate rounds at the approved limit and stop remedial work when any hard ceiling is hit.
- [x] 2.3 Split admin-curation waiting into admission-stage and execution-stage monitoring with explicit terminal reasons.
- [x] 2.4 Change admin-curation translation defaults so terminology-table generation is off while structured insight generation remains on.
- [x] 2.5 Bound deterministic upstream fatal errors so quota/auth/model failures do not loop through rescue work.
- [x] 2.6 Reconcile cancellation handling so timeout/budget-triggered cancellation both terminates the live backend execution and writes terminal persisted task state.
- [x] 2.7 Expose stable terminal reasons through task status and admin-curation status payloads.

## 3. Verification

- [x] 3.1 Add or update tests for remedial-budget accounting and exhaustion.
- [x] 3.2 Add or update tests for queue/admission time not consuming execution timeout.
- [x] 3.3 Add or update tests proving canceled or timed-out runs cannot remain stuck in `processing`.
- [x] 3.4 Add or update tests proving timeout/budget-triggered cancellation actually terminates the live backend execution path.
- [x] 3.5 Add or update tests proving fatal upstream-provider errors short-circuit within the bounded policy.
- [x] 3.6 Add or update tests proving terminal reasons are returned by task and curation status APIs.

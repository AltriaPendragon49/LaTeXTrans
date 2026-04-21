# Change: bound remedial translation retries and split admin-curation timeout budgets

## Why

Production admin-curation runs are currently spending too much budget on repeated rescue loops while also failing papers for a coarse 30-minute wall clock that includes download, queue wait, and actual translation execution. This creates two bad outcomes at once: abnormal LLM spend on pathological papers and false timeout failures for papers that did not actually receive 30 minutes of translation work.

## What Changes

- Add explicit remedial-attempt accounting for translation rescue flows and cap each major retry layer.
- Split admin-curation time control into admission-stage waiting and execution-stage monitoring instead of one shared 30-minute wall clock.
- Require deterministic terminal behavior when retry or timeout budgets are exhausted so tasks cannot linger in `processing`.
- Require any cancellation path triggered by timeout or budget exhaustion to both persist a terminal task state and actually terminate the live backend execution.
- Bound repeated fatal upstream-provider failures so authentication/quota/model-availability errors cannot amplify rescue spend.
- Expose stable machine-readable terminal reasons and curation timeout reasons through backend status surfaces.
- Change admin-curation translation defaults to keep structured insight generation enabled but disable terminology-table generation for curation-triggered translations.

## Impact

- Affected specs: `translation-orchestration`, `community-admin-curation`, `task-cancellation`, `web-api`
- Affected code: translator rescue orchestration, upstream-provider error routing, admin curation polling/wait logic, task cancellation/failure reconciliation, curation translation config defaults, task-status/admin-status response shaping

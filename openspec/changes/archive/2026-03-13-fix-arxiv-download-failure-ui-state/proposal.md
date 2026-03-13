# Change: Fix ArXiv Download Failure UI State

## Why
When arXiv source download fails due to network interruption, backend correctly marks task status as `failed`, but frontend can still show a success state due to unconditional handling of SSE `complete` events.

## What Changes
- Update frontend download-state handling so SSE `complete` is status-aware.
- Ensure `failed`/`failed_compilation`/`structure_invalid` terminal statuses are rendered as failure in the download flow.
- Prevent success toast and `Source Ready` badge from being shown when terminal status is failed.

## Impact
- Affected specs: `web-ui`
- Affected code:
  - `frontend/src/store/useStore.ts`

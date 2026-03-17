## Why
- Batch translation tasks on the dashboard can stop polling after a fixed timeout even though the backend keeps processing them.
- When later tasks finally complete, the batch panel can remain stuck on a stale non-terminal status like "准备编译中", while the history page already shows the correct terminal state.
- This creates false negatives in the active UI and makes users think compilation is hung even though the PDF already exists.

## What Changes
- Keep batch-task polling alive until the task reaches a terminal status or the batch component unmounts.
- Prevent duplicate pollers for the same batch task so repeated submissions or rerenders do not fan out extra requests.
- Clarify that the batch task list must continue reflecting backend terminal states even when compile queue wait time exceeds the original polling window.

## Impact
- Affects frontend batch translation task tracking in `BatchTranslation.tsx`.
- Keeps dashboard batch task cards consistent with task history and backend task status APIs.
- Adds no backend API changes.
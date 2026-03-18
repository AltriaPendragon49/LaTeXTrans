# Why
- Day 2 converts existing upload and arXiv import paths into a unified `paper` entry flow.
- Feed and paper detail work cannot proceed safely until the intake and read APIs share one paper-centric contract.
- This change creates the backend contract that later UI and translation bridge changes depend on.

## What Changes
- Define the submit, list, detail, and view event API slice for papers.
- Define how a paper record maps to translation tasks and local assets.
- Limit scope to intake and read models so translation actions remain in Day 4.

## Impact
- Adds capability `community-paper-intake-api`.
- Depends on `add-community-day-01-schema-rls-foundation`.
- Provides the backend contract used by Day 3 and Day 4 changes.

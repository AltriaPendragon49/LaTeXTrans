# Why
- Day 2 converts existing upload and arXiv import paths into a unified `paper` entry flow.
- Feed and paper detail work cannot proceed safely until the intake and read APIs share one paper-centric contract.
- The product boundary is now clearer: the community is an officially curated paper feed, while user translations only fill gaps when no official version exists.
- This change creates the backend contract that later UI and translation bridge changes depend on.

## What Changes
- Refine the `papers` schema with explicit community-admission and community-selection fields.
- Define the submit, list, detail, and view event API slice for papers under an “official-first, user-fallback” community model.
- Define how a paper record maps to translation tasks and local assets.
- Define how official submissions override user fallback visibility for the same `arxiv_id`.
- Limit scope to intake and read models so translation actions remain in Day 4.

## Impact
- Adds capability `community-paper-intake-api`.
- Depends on `add-community-day-01-schema-rls-foundation`.
- Adds an additive migration on `public.papers` only; existing `translation_tasks` and `user_settings` remain untouched.
- Provides the backend contract used by Day 3 and Day 4 changes.

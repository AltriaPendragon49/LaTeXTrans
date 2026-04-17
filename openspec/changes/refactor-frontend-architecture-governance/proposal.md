# Change: Formalize frontend architecture governance for incremental refactor

## Why
The current frontend structure is still primarily organized by technical file type (`pages/`, `components/`, `hooks/`, `lib/`, `store/`) rather than by architectural responsibility. That makes page ownership, shared-business boundaries, and migration sequencing hard to understand for both humans and AI collaborators.

We need a formal architecture record before any page-by-page refactor starts so future work can follow consistent rules instead of ad hoc judgment.

## What Changes
- Add a new OpenSpec capability for frontend architecture governance and migration rules
- Define hard classification rules for `ui/`, `features/`, and `pages/<page>/...`
- Define page-vs-feature boundaries, hook placement rules, and naming conventions
- Define compatibility-first migration rules, including re-export transitions and behavior-preserving phases
- Define anti-over-fragmentation rules so the refactor does not create unnecessary file churn
- Record `PaperDetail` as the first single-page pilot blueprint for future migration planning only

## Impact
- Affected specs: `frontend-architecture-governance`
- Affected code: future work under `frontend/src/**/*`
- Runtime impact in this change: none
- Delivery mode: planning/specification only; no frontend implementation starts under this change until approval

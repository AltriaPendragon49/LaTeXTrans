<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

# Project Skill Routing

In this repository, prefer the following skills when they match the user's request.

## Default Entry Skills

- `using-superpowers`
  Use as the default skill discipline for checking and invoking relevant skills before acting.
- `superpowers-openspec-bridge`
  Use when the user wants to brainstorm first, formalize later, follow the repo's preferred workflow, or combine Superpowers with OpenSpec.

## Formal Record

- Superpowers skills remain enabled in this repository as process tools for brainstorming, planning, debugging, verification, and review.
- OpenSpec under `openspec/` is the only formal documentation carrier for active design, change, task, and migration records.
- Do not create or update active workflow artifacts outside OpenSpec.
- When a Superpowers skill would normally emit a design doc, plan, or similar formal artifact, write the result into the relevant `openspec/changes/<change-id>/...`, `openspec/specs/...`, or `openspec/changes/archive/...` location instead.

## Planning And Spec Work

- `brainstorming`
  Use before creative implementation work, new features, behavior changes, architecture decisions, or unclear requests that need design refinement. Preserve the brainstorming process, but formalize approved outputs into OpenSpec.
- `planning-with-files`
  Use for complex multi-step work when persistent markdown planning files would help track progress or decisions.

## OpenSpec Boundary

When the request introduces a new capability, intentional behavior change, architecture change, breaking change, or major security/performance behavior change:

1. Prefer `superpowers-openspec-bridge`
2. Use `brainstorming` to refine the design
3. Formalize the approved direction in OpenSpec
4. Do not implement until the OpenSpec proposal is approved

When the request is a bug fix restoring intended behavior, a test-only change, a non-breaking config update, or a behavior-preserving refactor:

1. OpenSpec proposal is usually not required
2. Use the relevant Superpowers execution skill directly

## Execution Skills

- `writing-plans`
  Use after design approval or after an approved OpenSpec change when a detailed execution breakdown is still needed. Any written plan artifact must live under OpenSpec.
- `systematic-debugging`
  Use for bugs, regressions, flaky behavior, or unknown root-cause investigation.
- `test-driven-development`
  Use when implementing behavior changes or bug fixes where test-first discipline is appropriate.
- `verification-before-completion`
  Use before declaring a bug fix or implementation complete.
- `requesting-code-review`
  Use before finishing substantial code changes.
- `dispatching-parallel-agents`
  Use only when there are multiple independent tasks that can safely proceed in parallel.

## Domain Skills

- `frontend-design`
  Use for new UI, page, or component work where design quality matters.
- `i18n-engineering`
  Use for user-visible copy or locale-sensitive frontend changes under `frontend/`.
- `backend-patterns`
  Use for API, service, repository, middleware, auth, or backend architecture work.
- `security-review`
  Use when touching auth, secrets, user input, payments, or sensitive flows.
- `supabase-postgres-best-practices`
  Use for Postgres schema, SQL, indexes, constraints, or query optimization work involving Supabase/Postgres.
- `vercel-react-best-practices`
  Use when writing or refactoring React or Next.js code where performance and modern patterns matter.

## Documentation Lookup Skills

- `documentation-lookup` or `context7-docs-lookup`
  Use when framework or library behavior should be confirmed from current documentation rather than memory.

## Skill Preference For This Repo

Preferred high-level workflow:

1. `superpowers-openspec-bridge` for feature or architecture work
2. `brainstorming` for refinement
3. OpenSpec for formal proposal/spec/tasks
4. `writing-plans` only after approval if deeper execution planning is useful, with output stored under OpenSpec
5. Execution with debugging, TDD, verification, and review skills as needed

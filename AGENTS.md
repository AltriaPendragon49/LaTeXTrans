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
  Use for complex multi-step work when persistent markdown planning files would help track progress or decisions. Any persistent planning artifact must live under OpenSpec.

## OpenSpec Boundary

When the request introduces a new capability, intentional behavior change, architecture change, breaking change, or major security/performance behavior change:

1. Prefer `superpowers-openspec-bridge`
2. Use `brainstorming` to refine the design
3. Formalize the approved direction in OpenSpec
4. Do not implement until the OpenSpec proposal is approved

When the request is a bug fix restoring intended behavior, a test-only change, a non-breaking config update, or a behavior-preserving refactor:

1. OpenSpec proposal is usually not required
2. Use the relevant Superpowers execution skill directly

## Execution Discipline

Apply the following execution principles during coding, debugging, refactoring, and verification. These principles do not replace OpenSpec or Superpowers routing; they constrain implementation behavior after the correct workflow has been selected.

### Think Before Coding

Before editing code, identify:
- The concrete user goal
- The smallest set of files likely involved
- The expected behavior after the change
- The verification command or observable check that proves completion

Do not start broad rewrites before understanding the intended behavior and current implementation path.

### Simplicity First

Prefer the simplest change that satisfies the accepted requirement.

Avoid:
- Unnecessary new abstractions
- New frameworks or heavy dependencies without a clear need
- Rebuilding a subsystem when a targeted fix is enough
- Expanding the task beyond the user's stated goal

When restoring old behavior, prioritize matching the old behavior exactly over introducing a cleaner but behaviorally different design.

### Surgical Changes

Keep modifications narrow and intentional.

Do not:
- Rewrite unrelated files
- Reformat large areas without need
- Rename files, functions, or public contracts unless required
- Change behavior outside the requested scope
- Mix cleanup work with feature or bug-fix work unless the cleanup is necessary for the change

If unrelated issues are discovered, mention them separately instead of silently fixing them in the same change.

### Goal-Driven Execution

Every implementation step should connect back to the user's goal.

Before declaring completion, verify:
- The requested behavior is implemented
- The relevant tests, build, typecheck, lint, or manual checks have been run when available
- Any skipped verification is explicitly stated with the reason
- Known remaining risks or limitations are called out

Do not claim completion based only on code inspection when a reasonable verification path exists.

### Preserve Existing Contracts

Maintain compatibility with existing APIs, database schema, task states, frontend props, persisted data, and public routes unless the approved OpenSpec change explicitly allows changing them.

For behavior-preserving refactors:
- Inputs and outputs must stay equivalent
- Existing tests should continue to pass
- User-visible behavior should not drift

### Avoid Hidden Scope Expansion

If a request is narrow, keep the work narrow.

For example:
- A backend bug fix should not trigger a frontend redesign
- A UI style adjustment should not rewrite state management
- A translation pipeline rollback should not introduce a new orchestration architecture unless approved
- A config update should not alter runtime behavior beyond the stated config goal

### Verify Before Completion

Use `verification-before-completion` before declaring a bug fix, implementation, or refactor complete.

Verification should be proportional to the change:
- Small config or copy change: targeted inspection or minimal command is acceptable
- Frontend change: build, typecheck, relevant tests, or browser/manual route check when available
- Backend change: unit tests, integration tests, compile check, API health check, or targeted script
- Database/migration change: migration dry-run or clear manual verification path
- Translation pipeline change: representative task run or minimal reproducible pipeline check when feasible

If verification cannot be run, state exactly what was not run and why.

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

## Backend Index Discipline

- When the task needs backend file lookup, backend structure orientation, or fast module discovery, read `backend/file.md` first.
- Treat `backend/file.md` as the preferred backend path index for AI scanning before doing broader backend file searches.
- If any backend production file is added, deleted, moved, or renamed, updating `backend/file.md` in the same change is mandatory.
- If a backend file's real responsibility changes materially, update its description in `backend/file.md` as part of the same work, use Chinese in UTF-8.

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

## Practical Priority Rules

When multiple rules appear to apply, use this priority order:

1. User safety and repository security
2. OpenSpec boundary rules
3. Formal record location under `openspec/`
4. Project skill routing
5. Backend index discipline
6. Execution discipline: think first, keep it simple, make surgical changes, verify before completion

For major feature or architecture work, never bypass OpenSpec by treating the change as a simple implementation task.

For small bug fixes or config updates, do not over-process the task with unnecessary proposals; use the relevant execution skill directly and keep the change minimal.
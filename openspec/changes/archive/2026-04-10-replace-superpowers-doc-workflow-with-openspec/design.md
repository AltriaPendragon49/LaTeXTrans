## Context

The repository already states that OpenSpec is the formal planning and change-management system, but active assistant workflows still generate documents into `docs/superpowers/specs/` and `docs/superpowers/plans/`. That creates two problems:

1. design and execution records can exist outside OpenSpec
2. the route used by Superpowers skills conflicts with the repository's desired OpenSpec-only workflow

At the same time, the team does not want to lose Superpowers itself. Brainstorming, writing-plans, verification, review, and routing behavior remain valuable. The change must therefore separate **process capability** from **formal documentation carrier**.

## Goals

- Keep Superpowers skills available and functionally intact
- Make OpenSpec the only formal carrier for change, design, and execution records
- Migrate every active `docs/superpowers/*` file into `openspec/`
- Remove repository and local skill instructions that still auto-generate `docs/superpowers/*`
- Leave a verification trail that proves both document unification and skill-preservation

## Non-Goals

- Removing Superpowers skills
- Replacing brainstorming, planning, verification, or review with a weaker process
- Rewriting unrelated product specs
- Reorganizing archived historical OpenSpec material beyond what is required to host the migrated files

## Decisions

### Decision: OpenSpec becomes the sole formal documentation carrier

For this repository, any formal design, change, task, execution, or migration record that is part of active engineering truth must live under `openspec/`.

Allowed destinations:

- `openspec/changes/<change-id>/proposal.md`
- `openspec/changes/<change-id>/design.md`
- `openspec/changes/<change-id>/tasks.md`
- additional supporting records under `openspec/changes/<change-id>/`
- `openspec/specs/<capability>/spec.md`
- `openspec/changes/archive/...` for archived historical records

Disallowed destination for active formal workflow output:

- `docs/superpowers/**`

### Decision: Superpowers remains a process layer, not a competing spec store

The repository will keep Superpowers for:

- idea refinement
- approach comparison
- execution decomposition
- debugging discipline
- verification discipline
- review discipline

The change only updates where those skills record their outputs. Their effect must remain intact:

- `brainstorming` still performs design exploration and approval gating
- `writing-plans` still decomposes approved work into actionable tasks
- `verification-before-completion` still requires evidence-before-claims
- `using-superpowers` and routing skills still govern when these process skills are used

### Decision: Legacy Superpowers documents are migrated by explicit mapping rules

The current repository has five active `docs/superpowers/*` files. They will be migrated using the following rules:

| Source | Target strategy |
| --- | --- |
| `docs/superpowers/specs/2026-04-09-supabase-replacement-local-design.md` | Fold into `openspec/changes/replace-supabase-with-niutrans-auth-and-mysql/design.md` or a supporting document under that same change |
| `docs/superpowers/specs/2026-04-09-central-authorization-design.md` | Fold into the same approved auth-migration change because the content describes the centralized authorization workstream that already lives there |
| `docs/superpowers/plans/2026-04-09-central-authorization-plan.md` | Convert into OpenSpec-native execution/supporting material under `openspec/changes/replace-supabase-with-niutrans-auth-and-mysql/` |
| `docs/superpowers/specs/2026-04-10-processing-page-balance-design.md` | Preserve inside OpenSpec as a migrated historical design note because it reflects an implemented UI balancing pass that was not formalized through its own change package |
| `docs/superpowers/plans/2026-04-10-processing-page-balance.md` | Preserve beside the migrated historical design note or condense into the same migrated note if duplication is high |

The migration should favor the most semantically relevant OpenSpec location, not a blind copy into one bucket.

### Decision: Repository routing and local skill prompts both need updating

Changing only repository files is insufficient because the current auto-generation path is reinforced by machine-local skill prompts. The migration must therefore cover both:

- repository instructions such as `AGENTS.md`
- repository-local skills under `.codex/skills/**` if they route outputs to `docs/superpowers/**`
- machine-local Superpowers skill files under `C:/Users/xhs/.codex/superpowers/skills/**`

The skill edits must preserve the process semantics while replacing output paths and wording so the formalized result lands in OpenSpec-compatible files and respects OpenSpec approval boundaries.

### Decision: Verification must prove both document unification and skill preservation

Success is not just "the old docs are gone." The verification set must show:

1. no active repository guidance still routes to `docs/superpowers/**`
2. no active local skill prompt still instructs the assistant to generate `docs/superpowers/**`
3. Superpowers process skills still exist and still describe brainstorming/planning/verification/review behavior
4. migrated repository documents now exist under `openspec/`

## Risks / Trade-offs

- Updating machine-local skill files affects this workstation outside the repository boundary, so a backup or diff capture is needed before rewriting them.
- Some `docs/superpowers/*` files are not one-to-one matches for existing OpenSpec files, so migration requires editorial judgment rather than pure file moves.
- If the migration only removes references but does not add a regression audit, the old document path may reappear later through another skill update.

## Migration Plan

1. Create the `developer-workflow` OpenSpec capability and validate the workflow rules formally.
2. Inventory all current `docs/superpowers/*` files and assign each one a target OpenSpec location.
3. Migrate the content into the selected OpenSpec files and remove `docs/superpowers/`.
4. Update repository workflow instructions so OpenSpec is the only formal carrier.
5. Update machine-local and repository-local skill prompts so Superpowers formalizes into OpenSpec-compatible files instead of `docs/superpowers/*`.
6. Run repository search, OpenSpec validation, and a skill-preservation audit.

## Open Questions

- None. The team explicitly chose the hard cut to OpenSpec-only formal documents while preserving Superpowers capabilities.

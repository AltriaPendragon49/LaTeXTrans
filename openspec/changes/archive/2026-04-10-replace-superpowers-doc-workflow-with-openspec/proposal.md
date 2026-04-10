# Change: Replace Superpowers Document Workflow With OpenSpec

## Why
The repository currently mixes two formal documentation carriers:

- OpenSpec under `openspec/`
- Superpowers-generated design/plan files under `docs/superpowers/`

That split creates duplicate sources of truth, lets assistant workflows auto-generate active documentation outside OpenSpec, and leaves repository guidance and local skill prompts out of sync with the repo's stated OpenSpec-first process.

The team wants to keep Superpowers as a process layer for brainstorming, planning, verification, and review, but move all formal change/design/plan records into OpenSpec and eliminate the competing `docs/superpowers/` track.

## What Changes
- Add an OpenSpec capability that defines repository workflow truth: OpenSpec is the only formal documentation carrier for design, change, and execution records.
- Preserve Superpowers skills and routing behavior as process aids, but update their document/output instructions so they formalize into OpenSpec-compatible locations and formats instead of `docs/superpowers/*`.
- Migrate all current `docs/superpowers/*` files into appropriate OpenSpec locations, using explicit mapping rules for active changes, archived history, and supporting migration records.
- Update repository workflow instructions and documentation to remove `docs/superpowers/*` as an accepted output target.
- Audit relevant repository-local and machine-local skill files so no active workflow still auto-generates Superpowers documents outside OpenSpec.
- Add verification steps to prove both goals at the same time:
  - no competing Superpowers document carrier remains active
  - Superpowers capabilities themselves were not deleted or weakened

## Impact
- Affected specs: `developer-workflow` (new)
- Affected repository files:
  - `AGENTS.md`
  - `docs/superpowers/**`
  - `openspec/changes/**`
  - repository-local workflow/skill guidance under `.codex/skills/**` where applicable
- Affected machine-local assistant guidance:
  - `C:/Users/xhs/.codex/superpowers/skills/**`
  - related local Codex skill files that currently direct outputs to `docs/superpowers/**`

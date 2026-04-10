## 1. OpenSpec Workflow Contract

- [x] 1.1 Add the `developer-workflow` capability delta defining OpenSpec as the only formal documentation carrier for repository workflow records.
- [x] 1.2 Validate the new change package with `openspec validate replace-superpowers-doc-workflow-with-openspec --strict --no-interactive`.

## 2. Migrate Existing Superpowers Documents Into OpenSpec

- [x] 2.1 Audit every file under `docs/superpowers/` and record its target OpenSpec destination before moving content.
- [x] 2.2 Migrate the Supabase replacement design and centralized authorization design/plan into the approved change `openspec/changes/replace-supabase-with-niutrans-auth-and-mysql/`.
- [x] 2.3 Preserve the processing-page balance design/plan inside `openspec/` as migrated historical workflow records.
- [x] 2.4 Remove `docs/superpowers/` after all migrated content exists under `openspec/`.

## 3. Replace Repository Workflow Routing

- [x] 3.1 Update `AGENTS.md` so it no longer routes formal workflow output to `docs/superpowers/*`.
- [x] 3.2 Update any active repository docs or local repo skill guidance that still references `docs/superpowers/*` as a valid output destination.
- [x] 3.3 Ensure repository workflow wording keeps Superpowers skills as process aids while naming OpenSpec as the sole formal record.

## 4. Replace Local Skill Output Targets Without Removing Skill Effects

- [x] 4.1 Back up or capture diffs for affected machine-local skill files under `C:/Users/xhs/.codex/superpowers/skills/**` before editing.
- [x] 4.2 Update `brainstorming` so its design formalization path targets OpenSpec-compatible change files instead of `docs/superpowers/specs/*`.
- [x] 4.3 Update `writing-plans` so its planning output targets OpenSpec-compatible change files instead of `docs/superpowers/plans/*`.
- [x] 4.4 Update any other relevant local or repository skill/router prompts that still treat Superpowers documents as the formal output carrier.
- [x] 4.5 Review the edited skill text to confirm brainstorming, planning, verification, review, and routing behavior still exist and were not weakened.

## 5. Regression Audit And Verification

- [x] 5.1 Run a repository-wide search and confirm no active `docs/superpowers` references remain outside archived history or intentional migration notes.
- [x] 5.2 Run a local skill audit and confirm no active machine-local or repository-local skill still instructs generation of `docs/superpowers/*`.
- [x] 5.3 Run `openspec validate replace-superpowers-doc-workflow-with-openspec --strict --no-interactive` after all edits are complete.
- [x] 5.4 Record a final capability-preservation review that explicitly confirms Superpowers skills still exist and still provide their original process effects with OpenSpec as the formal carrier.

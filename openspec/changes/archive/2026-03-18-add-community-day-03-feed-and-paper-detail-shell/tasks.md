## 1. OpenSpec Alignment
- [x] 1.1 Update Day 3 proposal/spec/tasks to reflect the community-first homepage, `/translate` workspace relocation, and alphaXiv-inspired design direction.
- [x] 1.2 Add `design.md` documenting route migration, visual system, disabled action slots, accessibility rules, and alphaXiv reference boundaries.
- [x] 1.3 Add a Day 3 delta for `web-ui` so the homepage contract no longer points at the old Dashboard.

## 2. Frontend Delivery
- [x] 2.1 Add the community Feed homepage shell at `/` with latest, translated, and hot views backed by Day 2 APIs.
- [x] 2.2 Add the paper detail shell at `/paper/:paperId` with metadata, abstract, selected asset summary, and disabled action slots.
- [x] 2.3 Relocate the existing translation Dashboard to `/translate` and update sidebar navigation to surface both Community and New Translation.
- [x] 2.4 Implement the restrained graphite-dark editorial treatment using the project UI primitives, `ui-ux-pro-max`, and `frontend-design` guidance.

## 3. Quality Gates
- [x] 3.1 Add tests covering community Feed rendering, detail rendering, route migration, and paper card behavior.
- [x] 3.2 Update locale resources for all required community UI copy without introducing pending i18n placeholders.
- [x] 3.3 Run the targeted frontend test suite plus `npm run i18n:check`.
- [x] 3.4 Run `openspec validate add-community-day-03-feed-and-paper-detail-shell --strict --no-interactive`.

## 4. Status Sync
- [x] 4.1 Mark every completed item in this checklist.
- [x] 4.2 Update Day 3 status in `texts/社区打造十天OpenSpec执行索引.md` after all implementation and validation steps pass.

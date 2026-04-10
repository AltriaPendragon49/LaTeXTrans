## 1. Backend Contracts And Persistence
- [x] 1.1 Add admin-only community curation data and API contracts for single and batch intake via `arXiv ID` and TeX archives.
- [x] 1.2 Add canonical-paper identity and dedupe rules so repeated curation reuses an immutable `paper_id` and overwrites the existing canonical paper in place.
- [ ] 1.3 Add archive metadata extraction so title and abstract are available for community feed cards before publication.
- [ ] 1.4 Add structured insight persistence with the minimum section schema for English and Chinese and gate public publication on insight readiness.
- [x] 1.5 Add persistent async hard delete that immediately hides the paper, removes all related storage/index/cache artifacts, and keeps retrying until cleanup completes.
- [x] 1.6 Stop ordinary tool translations from auto-publishing or scheduling community publication watches.
- [x] 1.7 Add homepage search backend rules that only return formal public community papers and never mix in tool results, incomplete items, or deleting records.

## 2. Frontend Community Surfaces
- [x] 2.1 Replace the homepage public agent composer with internal community search while preserving the existing overall layout feel.
- [x] 2.2 Add admin-only homepage controls: sidebar curation entry and per-card delete action.
- [x] 2.3 Replace the paper-detail public agent pane with collapsible structured insight modules that follow the current reader language mode.
- [x] 2.4 Add the new admin-only community curation page with single and batch submission for `arXiv ID`s and archive uploads.
- [x] 2.5 Hide homepage, sidebar, and paper-detail public agent entry points and ensure the retained community-agent product routes are not directly usable in the current hidden mode.

## 3. Verification
- [ ] 3.1 Add/update backend tests for admin auth, canonical identity reuse, archive metadata extraction, bounded-concurrency batch intake, per-item batch failure semantics, publication gating, and persistent hard delete retry.
- [x] 3.2 Add/update frontend tests for search-first homepage behavior, public-search scoping, admin-only controls, hidden agent UI/access closure, and structured insight rendering.
- [x] 3.3 Validate the OpenSpec change and run focused manual smoke checks for normal-user tools, admin curation, and community deletion.

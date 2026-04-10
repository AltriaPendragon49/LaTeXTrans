# Acceptance Audit: Local Auth and MySQL Cutover

## Verdict

The active application code is using first-party auth plus the local database layer, not the retired third-party runtime.

## What Was Checked

- backend runtime auth paths
- backend persistence and recovery paths
- frontend auth bootstrap and API token usage
- dependency and env residue
- active docs and OpenSpec specs
- focused backend and frontend regression suites

## Acceptance Findings

### Runtime auth

- backend auth routes issue and verify local sessions through the project auth service
- frontend auth context reads and stores the local bearer token and bootstraps through `/api/auth/me`
- no active runtime auth path depends on third-party public keys or SDK clients

### Persistence

- task, history, settings, community paper, and community-agent flows are wired through local repository layers
- restart failover and orphan cleanup query the local translation-task repository
- the importer and migration docs now point at `import_source_to_mysql` naming

### Residue cleanup

- backend dependency manifest no longer declares the removed SDK
- backend and frontend `.env*` files no longer contain third-party auth env keys
- active locale files no longer keep stale third-party key names
- active README / docs / OpenSpec specs were updated to remove retired-provider runtime guidance

## Verification Evidence

### Repository search

The repo-wide search across `backend`, `frontend`, `docs`, and `openspec` was rerun after cleanup and returned `0 matches` for the removed provider naming, old env keys, and old importer paths inside active content.

### Backend tests

- `python -m pytest backend/tests/unit/test_restart_recovery_cleanup.py backend/tests/unit/test_import_source_to_mysql.py -q`
  - result: `16 passed`
- `python -m pytest backend/tests/unit/test_task_manager_flush_throttling.py backend/tests/unit/test_task_detail_metadata.py backend/tests/unit/test_task_manager_replay_quarantine.py backend/tests/unit/test_local_translation_task_persistence.py -q`
  - result: `27 passed`

### Paper and community regressions

- `python -m pytest backend/tests/unit/test_papers_list_detail_contract.py -q`
  - result: `9 passed`
- `python -m pytest backend/tests/unit/test_local_community_paper_persistence.py -q`
  - result: `3 passed`
- `python -m pytest backend/tests/unit/test_paper_service_local_write_cutover.py -q`
  - result: `6 passed`
- `python -m pytest backend/tests/unit/test_community_public_read_experience.py -q`
  - result: `11 passed`

### Frontend tests

- `npm.cmd run test -- AuthContext.local-auth.test.tsx History.test.tsx`
  - result: `2 test files passed, 2 tests passed`
- `npm.cmd run i18n:check`
  - result: `audit passed with warnings only`

### OpenSpec validation

- `openspec validate <approved-change-id> --strict --no-interactive`
  - result: `Change is valid`

## Acceptance Conclusion

This change passes the requested acceptance bar for active runtime behavior:

- first-party auth is the live auth path
- MySQL/local repository persistence is the live data path
- no active runtime dependency remains on the retired third-party service

## Totals Observed In This Verification Pass

- backend regression totals captured here: `72 passed`
- frontend targeted verification totals captured here: `2 passed`
- active residue search totals captured here: `0 matches`

## Notes

- the change directory name remains historical because it is the approved change id
- archived materials outside the active search scope were not used as runtime evidence

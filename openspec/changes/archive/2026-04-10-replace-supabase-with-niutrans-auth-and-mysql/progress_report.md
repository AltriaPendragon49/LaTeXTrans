# Change Progress Report: local-auth-and-mysql cutover

## Summary

This change completed the local-auth and MySQL migration work that replaced the retired third-party runtime paths with first-party auth, repository-backed persistence, and local import tooling.

## Completed Areas

- local login, bootstrap, and logout now rely on first-party auth endpoints
- translation history, settings, task persistence, and restart recovery now use local repositories
- community paper and community-agent persistence moved onto local repository layers
- importer tooling now uses `backend/scripts/import_source_to_mysql.py`
- env examples and active docs were cleaned to remove retired provider-specific runtime guidance

## Verification Status

- focused backend regression batches passed during the migration work
- targeted frontend auth/history tests passed in the current workspace
- OpenSpec validation for the approved change continues to pass after documentation cleanup

## Remaining Notes

- this file intentionally stays brief because the detailed acceptance evidence is maintained in `acceptance_audit.md`

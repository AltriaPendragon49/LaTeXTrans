# Change: Update product branding to PaperX

## Why
The product has moved beyond a narrowly framed LaTeX translation label, and the visible brand now needs to reflect the broader PaperX identity chosen for the site and logo. The implementation work is already complete, so this change records the intended branded surfaces and the cleanup of stale reader-highlight styling that is no longer part of the active product direction.

## What Changes
- Update visible frontend branding from LaTeXTrans/LaTexTrans to PaperX
- Switch the primary web logo and browser tab branding to the `paperx.png` asset
- Clean locale-managed community and reader copy so new PaperX-facing strings are translated per target language instead of leaving English, Chinese source text, or placeholder corruption in non-matching locales
- Align backend outward-facing brand strings such as API root metadata and status emails with PaperX
- Align hidden community-agent self-identification strings with PaperX where they can surface in generated copy
- Remove unused residual `::highlight(...)` CSS rules that were producing build warnings without active runtime highlight registration

## Impact
- Affected specs: `web-ui`, `web-api`
- Affected code: `frontend/index.html`, `frontend/src/components/app-sidebar.tsx`, `frontend/src/pages/ToolsHub.tsx`, `frontend/src/index.css`, `frontend/src/locales/*/common.json`, `backend/app/main.py`, `backend/app/core/config.py`, `backend/app/services/email_service.py`, `backend/app/api/routes/translate.py`, `backend/app/services/community_agent/orchestrator.py`, `backend/app/services/community_agent/skills/compose_academic_answer.py`, `backend/app/services/paper_service.py`

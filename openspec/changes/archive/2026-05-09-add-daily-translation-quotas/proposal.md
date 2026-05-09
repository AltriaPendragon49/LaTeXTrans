# Change: Add Daily Translation Quotas

## Why
Users need to see both the project's own daily LaTeX translation allowance and the PDF direct-translation credits returned by NiuTrans. The two quota sources have different meanings and must not offset each other.

## What Changes
- Fetch a safe NiuTrans user-info balance snapshot after local login and return/display the `unusedNumIntegral` value as PDF direct-translation credits.
- Add an independent local daily LaTeX translation quota of 3 items per authenticated user, resetting by UTC+8 natural day.
- Count ordinary arXiv ID translation and uploaded LaTeX/source-package translation against the same local LaTeX quota.
- Count batch translation per submitted paper/file; reject the whole batch before task creation when the requested item count exceeds remaining daily LaTeX quota.
- Keep NiuTrans PDF direct credits display-only for this feature; LaTeX quota and PDF direct credits do not deduct from each other.
- Expand the lower-left account/settings/logo area so it can show `LaTeX 翻译：3/3` on the left and `PDF 直译：<unusedNumIntegral>积分` on the right.

## Impact
- Affected specs: `user-auth`, `web-api`, `batch-translation`, `web-ui`
- Affected code:
  - `backend/app/services/auth_service.py`
  - `backend/app/api/routes/auth.py`
  - `backend/app/api/routes/translate.py`
  - `backend/app/api/routes/arxiv.py`
  - `backend/app/api/routes/upload.py`
  - `backend/app/repositories/auth_repository.py`
  - new quota repository/service and MySQL migration under `backend/`
  - `frontend/src/lib/local-auth.ts`
  - `frontend/src/contexts/AuthContext.tsx`
  - `frontend/src/layout/AppSidebar.tsx`
  - `frontend/src/features/user-workspace/components/WorkspaceAccountMenu.tsx`
  - `frontend/src/lib/api.ts`
  - frontend locale resources

# Change: Add PDF Direct Translation Workspace

## Why
The current translation workspace only exposes LaTeX-source translation entry points (`arXiv 编号`, `本地上传`, and `批量翻译`) under the existing LaTeX translation workflow. Users also need a PDF direct-translation product path that uploads editable PDF files, calls the existing NiuTrans paper-translation API, and consumes the user's PDF direct-translation credits instead of the local LaTeX daily quota.

## What Changes
- Reorganize the translation workspace so `LaTeX 翻译` and `PDF 直译` are first-level choices.
- Move `arXiv 编号`, `本地上传`, and `批量翻译` into a second-level option container under `LaTeX 翻译`.
- Add a dedicated `PDF 直译` workspace for authenticated users to upload editable PDFs, inspect page count/credit readiness, start direct translation, monitor progress, cancel running work, and download the translated PDF.
- Add backend proxy APIs that wrap the NiuTrans paper-translation endpoints from `texts/用户额度积分/文档翻译API接口文档-论文翻译API-V1.0.1(1).pdf`.
- Charge PDF direct translation against the logged-in user's own NiuTrans PDF direct-translation credits, keep those credits independent from the local LaTeX daily quota, and refresh quota snapshots after accepted PDF-direct operations.
- When the logged-in user's PDF direct-translation credits are insufficient, show a clear reminder with an action that opens the NiuTrans platform at `https://niutrans.com/`.
- Keep upstream NiuTrans credentials, auth strings, and raw upstream tokens server-side only.

## Impact
- Affected specs: `web-ui`, `web-api`, `pdf-direct-translation`
- Affected code: `frontend/src/features/translation-workflow/*`, `frontend/src/locales/*`, `frontend/src/contexts/AuthContext.tsx`, `backend/app/api/routes/*`, `backend/app/services/*`, `backend/app/repositories/translation_quota_repository.py`, `backend/app/core/config.py`, tests under `frontend/src/**` and `backend/tests/**`
- External dependency: NiuTrans document paper-translation API (`paperUploadAndGetPageNum`, `transPaperFile`, `getInfo`, `interrupt`, `download`)

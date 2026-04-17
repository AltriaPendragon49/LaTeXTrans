# Implementation Record

## Purpose
This document preserves the actual implementation and rollout details for the `update-cos-storage-and-api-ingress` change so the final production architecture and operator actions do not get lost in chat history.

## Final Outcome
- Production community assets now use Tencent COS as the canonical durable store.
- Production local disk is treated as a temporary cache for retained artifacts and is cleaned after successful COS persistence where applicable.
- The public frontend remains on Cloudflare Pages.
- The frontend now calls same-origin `/api/*` routes, and Pages Functions proxy those requests to the stable backend ingress.
- The backend ingress is now a persistent Cloudflare Named Tunnel instead of a temporary Quick Tunnel.
- Community translated PDF preview no longer depends on direct COS browser preview support; the first-party API proxies object-storage-backed preview PDFs inline.

## What Was Already Represented In OpenSpec Before This Record
The existing `proposal.md`, `design.md`, `specs/*`, and `tasks.md` already captured the intended high-level direction:
- Cloudflare-managed ingress instead of direct public origin exposure.
- COS-backed durable storage with local-disk fallback for development.
- Lightweight paper-detail bootstrap payloads with dedicated preview/PDF delivery paths.

Those files were directionally correct, but they did not fully preserve the final production routing decisions, the COS browser-preview limitation that was discovered during rollout, or the exact server-side operational steps that were required to stabilize the deployment.

## Gaps This Record Closes
- Documents that the temporary Quick Tunnel was only an interim workaround.
- Documents that the stable ingress solution is the pre-existing Named Tunnel `latextrans-api`.
- Documents that Tencent COS default-domain browser preview was not sufficient for translated PDF iframe rendering because the response was forced to download.
- Documents that translated PDF preview now uses a first-party proxy response while the explicit download route remains signed-URL based.
- Documents the final production service topology and the exact commands/actions performed on the production host.

## Timeline Of Work Completed

### 1. COS storage and community asset persistence
- Implemented a storage abstraction with `local_disk` and `cos`.
- Switched production retention behavior to upload canonical runtime and community assets to COS.
- Kept local development compatible by preserving local-disk mode.
- Verified canonical community assets for paper `2508.18791` on COS.

### 2. Lightweight detail bootstrap and reader delivery
- Slimmed the paper detail response so translated preview HTML is not embedded as a multi-megabyte payload in the base detail response.
- Kept dedicated preview and PDF fetch routes stable.
- Verified detail bootstrap, preview HTML fetch, source PDF fetch, and translated PDF fetch for the curated paper.

### 3. Public ingress debugging
- Confirmed the backend and host-local reverse proxy were healthy on the production host.
- Confirmed external direct access patterns were unstable when relying on the old browser-facing origin path.
- Introduced a Pages Functions same-origin `/api/*` proxy so the frontend no longer needs to expose a separate backend origin directly in browser code.

### 4. Temporary workaround during debugging
- A temporary Cloudflare Quick Tunnel was used as an intermediate workaround to restore external access while the stable ingress root cause was still being resolved.
- That Quick Tunnel URL was intentionally treated as non-durable and has now been superseded.

### 5. COS translated PDF preview root cause and fix
- Verified that object-storage-backed translated PDFs resolved through signed COS URLs.
- Verified that Tencent COS default-domain delivery still returned `Content-Disposition: attachment` and `x-cos-force-download: true` for the translated PDF object, which prevented reliable iframe preview behavior.
- Changed translated PDF preview delivery so the first-party API route `GET /api/papers/{paper_id}/translated-pdf` proxies the remote COS PDF back to the browser as an inline response.
- Preserved the dedicated download flow as a signed asset route so explicit downloads still work as downloads.

### 6. Stable ingress rollout
- Reused the existing Cloudflare Named Tunnel `latextrans-api`.
- Re-routed `api.latextrans.online` to that tunnel.
- Installed the tunnel credentials and config on the production server.
- Created a persistent `cloudflared.service` systemd unit on the production server.
- Stopped using the temporary Quick Tunnel process.
- Updated the frontend Pages proxy default upstream from the temporary `trycloudflare.com` URL to `https://api.latextrans.online`.
- Redeployed the frontend Pages project after the upstream switch.

## Production Architecture After Rollout

### User-facing entrypoints
- Frontend application: `https://latextrans.niutrans.com`
- Stable backend ingress: `https://api.latextrans.online`

### Frontend request flow
1. Browser loads `https://latextrans.niutrans.com`.
2. Frontend requests same-origin `/api/*`.
3. Cloudflare Pages Functions forwards `/api/*` to `https://api.latextrans.online`.
4. Cloudflare Named Tunnel routes traffic from `api.latextrans.online` to the production server backend on `127.0.0.1:9001`.

### Backend and storage flow
1. Translation/runtime stages use local filesystem working directories while tasks execute.
2. Retained artifacts are uploaded to Tencent COS.
3. Published community assets store canonical object-storage references in `paper_assets`.
4. Preview HTML is read through backend-aware resolution.
5. Source PDF continues to use the existing source preview path.
6. Translated PDF preview uses a first-party proxy response for object-storage assets.
7. Explicit translated PDF download uses the signed download route.

## Production Host State
- Server identity, SSH account, and filesystem layout are maintained outside Git in the controlled operations record.
- Backend service name is maintained in the controlled operations record.
- Stable Cloudflare tunnel service remains managed through `cloudflared.service`.
- Tunnel credential file path and tunnel ID are intentionally not preserved in repository documentation.
- Tunnel name: `latextrans-api`

## Important Implementation Files

### Backend
- `backend/app/services/storage_backend.py`
- `backend/app/services/paper_service.py`
- `backend/app/api/routes/papers.py`

### Frontend
- `frontend/functions/api/[[path]].ts`
- `frontend/functions/api/[[path]].test.ts`
- `frontend/src/api-base.test.ts`

### OpenSpec
- `openspec/changes/update-cos-storage-and-api-ingress/proposal.md`
- `openspec/changes/update-cos-storage-and-api-ingress/design.md`
- `openspec/changes/update-cos-storage-and-api-ingress/tasks.md`
- `openspec/changes/update-cos-storage-and-api-ingress/implementation-record.md`

## Validation Performed

### API and object-storage validation
- Verified `GET /api/health` through the frontend domain.
- Verified `GET /api/papers?sort=latest&limit=1`.
- Verified `GET /api/papers/{paper_id}` for the curated community paper.
- Verified `GET /api/papers/{paper_id}/preview` returns preview HTML.
- Verified `GET /api/papers/{paper_id}/translated-pdf` now returns first-party inline PDF content.
- Verified `Range` requests against `translated-pdf` return `206 Partial Content`.
- Verified explicit invalid download token returns `403`, preserving download-route protections.

### Admin and workflow validation
- Verified admin login with the provided administrator account.
- Verified admin curation for `2508.18791`.
- Verified the curated paper reached completed/published state.

### Frontend validation
- Verified frontend build succeeds after the proxy changes.
- Verified Pages Functions proxy tests pass.
- Captured screenshots for homepage and paper detail after ingress stabilization.

## Commits Produced During Rollout
- `2e82c1e` `fix: stabilize pages ingress and cos pdf preview`
- `ca400db` `fix: proxy translated pdf previews from object storage`
- `6d60ab1` `fix: point pages api proxy at stable tunnel domain`

## Current Known Caveats
- Local DNS caches may continue to resolve `api.latextrans.online` to the old origin briefly after the DNS cutover; public resolvers already return the Cloudflare edge addresses.
- The translated PDF preview path now intentionally uses first-party proxying for object-storage assets because COS default-domain browser preview behavior was not sufficient for iframe rendering.
- The frontend Pages deployment warning about `wrangler.toml` missing `pages_build_output_dir` does not block deployment, but the config can be cleaned up later.

## 2026-04-12 Regression Follow-Up

### Problems re-verified after the COS and ingress rollout
- Public structured analysis for the curated paper regressed to fallback placeholder copy.
- Community detail pages were still eagerly pulling translated PDF resources on first entry.
- The homepage was still triggering translated PDF thumbnail work too early.
- The translated HTML reader remained the slowest public path because it depends on a multi-megabyte preview payload.

### Additional fixes and operator actions completed
- Regenerated `community_structured_insights` in production for paper `2508.18791` by running the structured-insight rebuild flow inside the backend container against the persisted COS-backed preview asset. The live API now returns five readable analysis sections instead of fallback text.
- Added a dedicated frontend preview-origin setting so translated HTML preview fetches can bypass the Pages same-origin proxy when enabled, while still falling back to the existing route if the direct fetch fails.
- Delayed homepage translated-PDF thumbnail rendering until browser idle time or user intent, so the homepage no longer immediately starts large translated-PDF range requests during the first paint.
- Disabled the translated HTML reader in production UI via environment configuration while keeping preview HTML generation intact on the backend. This preserves structured-analysis generation and any future internal preview recovery flows, but removes the slow public entrypoint from normal production usage.

### Acceptance evidence captured
- Homepage re-check: within the first several seconds after load, the only community resource request observed was `GET /api/papers?sort=latest`; the translated PDF thumbnail request no longer fires immediately.
- Detail re-check: the structured-analysis panel renders real section prompts and content again for paper `2508.18791`.
- Detail re-check: the translated HTML mode button is present but disabled in production, preventing users from entering the slow public HTML reader path while backend preview assets remain available for analysis.
- Screenshot and browser-capture artifacts were saved locally under:
  - `artifacts/selenium/`
  - `artifacts/selenium-post-deploy/`
  - `artifacts/selenium-final/`

## Conclusion
The active OpenSpec change now has both the original formal proposal/design/spec deltas and this concrete implementation record. That means the repository preserves:
- the intended architecture,
- the final production architecture,
- the exact rollout actions,
- the operational state required to keep the deployment stable.

## 2026-04-12 PDF Reader Performance Tuning

### Regressions addressed in this pass
- Homepage paper-card previews were still expensive because they relied on `react-pdf` canvas rendering inside every visible card.
- Detail pages still defaulted into translated PDF when translated HTML was unavailable in production, which made the first open feel slower than necessary.
- The translated PDF proxy path for COS-backed assets still buffered the full upstream file before responding, weakening the benefit of object storage for iframe viewing.
- The standalone and bilingual PDF readers opened without an explicit page-fit fragment, and the translated PDF reader still used a fixed height, which contributed to the "page does not fully fit on first open" regression.

### Code changes completed
- Replaced homepage paper-card PDF canvas previews with lightweight thumbnail images served from new backend routes:
  - `GET /api/papers/{paper_id}/source-thumbnail`
  - `GET /api/papers/{paper_id}/translated-thumbnail`
- Added temporary thumbnail caching under `backend/data/tmp_storage/paper_pdf_thumbnails/` so first-page PNGs are reused instead of regenerated on every request.
- Changed the homepage translated preview to load only after explicit user intent on the card, while preserving the existing visual layout with placeholder frames.
- Updated detail-page reader mode resolution so the page falls back to `source` before `translated_pdf` when the preferred mode is unavailable.
- Updated PDF iframe URLs to include `#page=1&zoom=page-fit` and changed the translated PDF reader to fill the available height again.
- Increased the default reader/sidebar split ratio from `0.65` to `0.7` to give the PDF workspace more room without materially changing the surrounding layout.
- Reworked the COS translated-PDF proxy into a true streaming response that forwards Range requests and no longer buffers the full upstream PDF in memory before responding.

### Validation completed
- Frontend targeted tests passed:
  - `src/components/community/PaperCard.test.tsx`
  - `src/pages/PaperDetail.test.tsx`
  - `src/pages/PaperDetail.reader-first.test.tsx`
- Frontend production build passed with `npm run build`.
- Backend targeted route tests passed:
  - `backend/tests/unit/test_papers_route_asset_redirects.py`

### Deployment intent for this pass
- Push the updated `main` branch.
- Pull `main` on the production host.
- Restart `latextrans-backend`.
- Redeploy the frontend bundle.
- Re-run live acceptance on homepage preview speed, detail PDF load speed, and bilingual compare first-open fit.

## 2026-04-13 PDF Loading Follow-Up

### Problems targeted in this pass
- Homepage source/translated preview thumbnails were still heavy enough to make the feed feel slow.
- Detail pages still had an avoidable first-open delay because the browser could end up opening the translated PDF path too early.
- Source-PDF preview for retained local files did not honor `Range` requests, so the browser could be forced into full-file reads.
- The bilingual compare reader needed a stronger "fit full page on first open" PDF fragment without changing the page layout width.

### Code changes completed
- Updated frontend detail-mode resolution so a backend `preferred_mode = translated` no longer forces the public page into translated PDF first; when public translated HTML is unavailable, the first-open path now falls back to source.
- Updated detail PDF URL resolution so source PDFs can use the reader-provided absolute source URL directly when available, instead of always routing back through `/api/papers/{paper_id}/source-pdf`.
- Changed PDF iframe fragments from `zoom=page-fit` to `view=Fit` plus hidden viewer chrome parameters, preserving the existing dual-column layout while biasing the embedded viewer toward full-page fit on first open.
- Added local-file `Range` support to both `GET /api/papers/{paper_id}/source-pdf` and `GET /api/papers/{paper_id}/translated-pdf`, so retained local previews now return `206 Partial Content` when the browser asks for byte ranges.
- Reworked thumbnail generation to produce smaller first-page PNGs directly at rasterization time and bumped the thumbnail cache version so production regenerated lighter cached previews.

### Production rollout completed
- Pushed `614e6f2` `fix: improve paper pdf loading behavior`.
- Pushed `2883d5d` `fix: shrink community paper thumbnails`.
- Pushed `8bdf398` `fix: regenerate lighter pdf thumbnails`.
- Pulled the updated `main` branch on the production host.
- Restarted the backend systemd service on the production host.
- Redeployed the Cloudflare Pages frontend; deployment URL for this pass was `https://a0066e3d.latextrans-bu2.pages.dev`.

### Live validation captured
- Backend health re-verified after restart through both `127.0.0.1:9001/api/health` on the host and `https://api.latextrans.online/api/health`.
- `GET /api/papers/{paper_id}/source-pdf` now returns `206 Partial Content` with `Accept-Ranges: bytes` for range requests.
- `GET /api/papers/{paper_id}/translated-pdf` continues to return `206 Partial Content` for range requests against COS-backed translated PDFs.
- Homepage thumbnail payloads for paper `2508.18791` were reduced from roughly `443860`/`551645` bytes to roughly `132552`/`147457` bytes.
- Browser automation against `https://latextrans.niutrans.com/paper/f5d8d23e96214d02ad4f21c23ebf0d4f` confirmed that the default visible reader is now the source PDF and that the source iframe opens directly against `https://arxiv.org/pdf/2508.18791.pdf#page=1&view=Fit...`.
- Browser automation confirmed bilingual compare still uses the existing dual-column layout while both iframes now carry the stronger `view=Fit` PDF fragment.

### Evidence and caveats
- Acceptance screenshots for this pass were saved locally under `artifacts/live-acceptance/`.
- Headless-browser screenshots do not render embedded PDF page contents faithfully; they are useful for verifying layout shell, active mode selection, iframe URLs, and the absence of unexpected UI regressions, but not for visually judging the rendered PDF text itself.

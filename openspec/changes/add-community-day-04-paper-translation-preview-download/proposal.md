# Why
- Day 3 delivered a community feed and paper detail shell, but the detail page still exposed placeholder actions instead of a real paper-owned translation bridge.
- The community MVP now needs a paper-centric path into the existing translation engine so a paper can be translated, monitored, previewed, and downloaded without forcing public readers through task-centric internal pages.
- The public paper surface must stay filesystem-safe and must not expose raw task download endpoints or local disk paths.

## What Changes
- Add a paper-owned translation entry at `POST /api/papers/{paper_id}/translate` that reuses the existing translation request contract.
- Add a public preview read path at `GET /api/papers/{paper_id}/preview` backed by a generated `preview_html` asset.
- Add a short-lived signed download flow using `POST /api/papers/{paper_id}/download-session` plus `GET /api/papers/{paper_id}/download?token=...`.
- Expand `paper_assets` syncing so successful translations attach `translated_pdf` and `preview_html` assets back to the paper.
- Upgrade the paper detail page into the translated public reading surface with inline HTML reader, progress jump, and controlled download actions.

## Impact
- Adds capability `community-paper-translation-bridge`.
- Depends on `add-community-day-03-feed-and-paper-detail-shell`.
- Touches backend paper routes/services, preview asset generation, download security, frontend community detail page, community API types, and locale files.

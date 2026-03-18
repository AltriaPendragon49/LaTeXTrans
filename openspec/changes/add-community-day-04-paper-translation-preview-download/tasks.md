## 1. Start Gate
- [x] 1.1 Confirm the Day 3 paper detail shell is the current action target.
- [x] 1.2 Mark Day 4 as `In Progress` in `texts/社区打造十天OpenSpec执行索引.md`.

## 2. Backend Delivery
- [x] 2.1 Add `POST /api/papers/{paper_id}/translate` as the paper-owned translation entry.
- [x] 2.2 Add `GET /api/papers/{paper_id}/preview`.
- [x] 2.3 Add signed download session + gateway behavior for public paper downloads.
- [x] 2.4 Sync `translated_pdf` and `preview_html` back into `paper_assets`.
- [x] 2.5 Add HTML preview generation from translated section maps.
- [x] 2.6 Add download-count RPC migration and backend tests.

## 3. Frontend Delivery
- [x] 3.1 Extend community API/types for translate, preview, and download session.
- [x] 3.2 Replace disabled action slots with real translate / progress / preview / download behavior on the paper detail page.
- [x] 3.3 Add inline translated reader with DOM sanitization and KaTeX rendering.
- [x] 3.4 Update locale files to cover new reader/action copy.

## 4. Validation And Sync
- [x] 4.1 Run `openspec validate add-community-day-04-paper-translation-preview-download --strict --no-interactive`.
- [x] 4.2 Update this task list to final truth.
- [x] 4.3 Update the Day 4 status in `texts/社区打造十天OpenSpec执行索引.md`.

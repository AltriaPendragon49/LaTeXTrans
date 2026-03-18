# Day 4 Design: Community Paper Translation Bridge

## Context
The existing translation platform is task-centric: upload/arXiv creation yields a task, `/processing` tracks the task, `/preview` compares original and translated PDFs, and `/download/*` streams task-owned files. Day 4 keeps that engine intact but introduces a paper-centric bridge so the community paper object becomes the public surface.

## Route Decisions
- Public paper page remains `/paper/:paperId`.
- `/processing` remains the internal progress surface.
- `/preview` remains the internal comparison surface for task workflows.
- Public community readers interact with paper routes, not raw task routes:
  - `POST /api/papers/{paper_id}/translate`
  - `GET /api/papers/{paper_id}/preview`
  - `POST /api/papers/{paper_id}/download-session`
  - `GET /api/papers/{paper_id}/download?token=...`

## Translation Bridge
### Existing task reuse
- If a paper already has `community_selected_task_id` and `trans_status in ('queued', 'processing')`, the bridge reuses that task instead of creating a duplicate.

### Local source reuse
- If the paper has a latest `source_archive` asset, the bridge creates a fresh task in memory, attaches `source_path`/`source_available`, then reuses the existing translation route to enqueue work.

### arXiv fallback
- If no local source asset exists but the paper still has `arxiv_id`, the bridge creates a new arXiv task and reuses the existing background download-and-enqueue pattern.

## Asset Sync
- The watcher keeps running after source availability instead of returning early.
- Source availability upserts `source_archive`.
- Translation completion resolves the translated PDF from task output and upserts `translated_pdf`.
- HTML preview generation reads translated section maps and writes `preview.html`, then upserts `preview_html`.
- `community_selected_asset_id` prefers `preview_html`, then `translated_pdf`, then `source_archive`.

## Inline Reader
- `preview_html` is generated from `sections_map.json` and placeholder maps already emitted by the translation pipeline.
- The HTML reader is intentionally semantic and minimal:
  - section/subsection/subsubsection map to headings
  - paragraphs render as `<p>`
  - LaTeX env placeholders are restored into readable blocks
  - inline and block math delimiters are preserved for frontend KaTeX rendering

## Public Asset Safety
- Community APIs expose asset metadata without `file_path`.
- Raw local disk paths stay internal to backend download and sync helpers only.

## Download Security
- Public papers may be downloaded anonymously, but only via a short-lived HMAC-signed token.
- The token payload includes version, `paper_id`, `asset_id`, and expiry.
- Download count increments only after the signed gateway successfully resolves the translated PDF.

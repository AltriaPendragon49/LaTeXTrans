## 1. Implementation
- [ ] 1.1 Add reusable source modes for `hot-top-n`, `hot-new-24h`, and `new-24h` to the export script
- [ ] 1.2 Normalize alphaXiv and arXiv records into one shared schema keyed by `arxiv_id`
- [ ] 1.3 Write Markdown and JSON outputs under `backend/arxiv_id/all_hot`, `backend/arxiv_id/daily_hot`, and `backend/arxiv_id/daily_new`, creating missing directories automatically
- [ ] 1.4 Filter malformed IDs and de-duplicate records within each export run
- [ ] 1.5 Encode source-priority metadata so downstream workflows can prefer `hot` and reuse already translated `new` papers without re-translation
- [ ] 1.6 Run the script for representative hot and new modes and verify the generated artifacts

## 1. Implementation
- [x] 1.1 Add reusable source modes for `hot-top-n`, `hot-new-24h`, and `new-24h` to the export script
- [x] 1.2 Normalize alphaXiv and arXiv records into one shared schema keyed by `arxiv_id`
- [x] 1.3 Write Markdown and JSON outputs under `backend/arxiv_id/all_hot`, `backend/arxiv_id/daily_hot`, and `backend/arxiv_id/daily_new`, creating missing directories automatically
- [x] 1.4 Filter malformed IDs and de-duplicate records within each export run
- [x] 1.5 Encode source-priority metadata so downstream workflows can prefer `hot` and reuse already translated `new` papers without re-translation
- [x] 1.6 Run the script for representative hot and new modes and verify the generated artifacts

## 2. Core Pool Upgrade
- [x] 2.1 Add a `core-pool` source mode and `backend/arxiv_id/core_pool/` output target
- [x] 2.2 Expand candidates from long-window `Views`, `Likes`, and `Comments` signals plus external impact metadata
- [x] 2.3 Add a recency cutoff so the core pool excludes very recent papers by default
- [x] 2.4 Implement arXiv-led category quotas with a minimum floor of 50 papers per included major category
- [x] 2.5 Export core-pool score breakdowns and selection metadata to JSON and Markdown
- [x] 2.6 Run the script for a representative `core-pool` build and verify the generated artifacts

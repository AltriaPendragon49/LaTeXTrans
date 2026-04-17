## Context
The repository currently has a sitemap-driven alphaXiv export script and pre-created source directories under `backend/arxiv_id/`:

- `backend/arxiv_id/all_hot/`
- `backend/arxiv_id/daily_hot/`
- `backend/arxiv_id/daily_new/`

alphaXiv and arXiv do not expose the same "daily new" set. Measured on April 17, 2026 UTC, alphaXiv hot papers published in the last 24 hours produced 32 valid unique IDs, while arXiv submissions in the last 24 hours produced 530 IDs, with only 29 IDs overlapping. This means the system must treat `hot` and `new` as distinct sources rather than assuming one can replace the other.

## Goals / Non-Goals
- Goals:
- Support a single reusable export entrypoint with three modes:
  - `hot-top-n`
  - `hot-new-24h`
  - `new-24h`
- Write outputs into the server-friendly `backend/arxiv_id/` directory tree
- Create both Markdown and JSON output files for human review and automation
- Enforce `arxiv_id` as the single de-duplication key across source modes
- Preserve source priority rules so `hot` intake always wins over `new` intake for translation scheduling
- Allow already translated papers discovered later from another source to be reused for ranking or display without triggering a second translation
- Non-Goals:
- Implement the downstream translation queue or ranking UI itself
- Persist paper-source state into the database in this change
- Replace future `daily_new` logic with alphaXiv-only discovery

## Decisions
- Decision: Keep one script entrypoint and add mode-based behavior.
- Alternatives considered: Separate scripts per source were rejected because they would duplicate parsing, validation, and file-output logic.

- Decision: Use alphaXiv feed APIs for `hot` modes and arXiv submitted-date queries for `new-24h`.
- Alternatives considered: Using alphaXiv alone was rejected because its recent hot papers are not equivalent to all recent arXiv submissions.

- Decision: Store source artifacts under `backend/arxiv_id/` and auto-create missing directories.
- Alternatives considered: Keeping outputs under `alphaxiv/` was rejected because the server workflow already expects source state under `backend/arxiv_id/`.

- Decision: Write both Markdown and JSON for every export.
- Alternatives considered: Markdown-only output was rejected because downstream automation needs a structured machine-readable format.

- Decision: De-duplicate globally by `arxiv_id`, with `hot` taking precedence over `new` for translation scheduling.
- Alternatives considered: Keeping separate translation copies per source was rejected because the paper library must not contain duplicate IDs.

- Decision: When a paper already translated from `new` later appears in `hot`, the system should not request a new translation.
- Alternatives considered: Re-translating under the `hot` source was rejected because it wastes compute and contradicts the one-paper-per-ID rule.

## Data Flow
1. The operator runs `scripts/export_alphaxiv_catalog.py` with a source mode.
2. The script resolves the correct upstream source:
   - alphaXiv hot feed for `hot-top-n`
   - alphaXiv hot feed filtered to the last 24 hours for `hot-new-24h`
   - arXiv submitted-date API for `new-24h`
3. The script normalizes each record to a shared schema keyed by `arxiv_id`.
4. The script removes invalid IDs and de-duplicates within the run.
5. The script writes both JSON and Markdown outputs into the matching `backend/arxiv_id/<subdir>/` location.
6. Downstream automation can merge these artifacts with the rule set:
   - translate `hot` papers first
   - skip translation when the paper is already translated
   - still keep the source occurrence available for ranking, display, or audit

## Output Shape
Each JSON entry should include at least:

- `arxiv_id`
- `title`
- `source_mode`
- `source_rank` when applicable
- `publication_date`
- `updated_at`
- `source_url`
- `exported_at`

The Markdown view should be a readable projection of the same dataset.

## Risks / Trade-offs
- alphaXiv feed responses contain malformed or non-paper IDs, so the script must validate IDs before output.
- alphaXiv and arXiv use different timestamps and freshness semantics, so the script must document which source field is used for filtering.
- The script can prepare source artifacts and de-duplication hints, but actual "already translated" checks may still depend on downstream systems not changed here.

## Migration Plan
1. Add a new OpenSpec change for the source-feed workflow.
2. Update the export script to support mode-based hot and new exports.
3. Write outputs into `backend/arxiv_id/` and create directories when missing.
4. Verify the script can generate the expected hot and new artifacts without duplicate IDs in a single export.

## Open Questions
- None for the first implementation. Downstream scheduling integration can build on the exported JSON metadata later.

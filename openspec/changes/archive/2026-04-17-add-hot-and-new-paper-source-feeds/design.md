## Context
The repository currently has a sitemap-driven alphaXiv export script and pre-created source directories under `backend/arxiv_id/`:

- `backend/arxiv_id/all_hot/`
- `backend/arxiv_id/daily_hot/`
- `backend/arxiv_id/daily_new/`
- `backend/arxiv_id/core_pool/` (to be created by the script if missing)

alphaXiv and arXiv do not expose the same "daily new" set. Measured on April 17, 2026 UTC, alphaXiv hot papers published in the last 24 hours produced 32 valid unique IDs, while arXiv submissions in the last 24 hours produced 530 IDs, with only 29 IDs overlapping. This means the system must treat `hot` and `new` as distinct sources rather than assuming one can replace the other.

The repository also needs a small pretranslated paper library. A plain alphaXiv hot feed is not sufficient for that purpose because it emphasizes momentum and platform-local activity. The evergreen subset should instead favor papers that are broadly recognized, heavily visited, and still representative of the wider research distribution, including lower-volume disciplines.

## Goals / Non-Goals
- Goals:
- Support a single reusable export entrypoint with the daily modes:
  - `hot-top-n`
  - `hot-new-24h`
  - `new-24h`
- Add a `core-pool` mode for building a low-frequency evergreen translation seed set
- Make `hot-top-n` default to the long-horizon `Hot + All time` view so the exported `all_hot` set reflects the most historically visitable papers rather than a short monthly window
- Write outputs into the server-friendly `backend/arxiv_id/` directory tree
- Create both Markdown and JSON output files for human review and automation
- Enforce `arxiv_id` as the single de-duplication key across source modes
- Preserve source priority rules so `hot` intake always wins over `new` intake for translation scheduling
- Allow already translated papers discovered later from another source to be reused for ranking or display without triggering a second translation
- Build the evergreen seed set around roughly 4000 papers
- Make the evergreen pool follow an arXiv-led category distribution with alphaXiv adjustments and a minimum category floor of 50 papers
- Non-Goals:
- Implement the downstream translation queue or ranking UI itself
- Persist paper-source state into the database in this change
- Replace future `daily_new` logic with alphaXiv-only discovery
- Perfectly infer global paper importance beyond the public signals available to the script

## Decisions
- Decision: Keep one script entrypoint and add mode-based behavior.
- Alternatives considered: Separate scripts per source were rejected because they would duplicate parsing, validation, and file-output logic.

- Decision: Use alphaXiv feed APIs for `hot` modes and arXiv submitted-date queries for `new-24h`.
- Alternatives considered: Using alphaXiv alone was rejected because its recent hot papers are not equivalent to all recent arXiv submissions.

- Decision: Default `hot-top-n` to alphaXiv `Hot` with `All time`.
- Alternatives considered: Using `30 Days` as the default was rejected because it overweights the current month and does not match the community goal of selecting the historically most likely-to-be-visited papers.

- Decision: Build the evergreen `core-pool` from multiple public signals instead of one alphaXiv ranking.
- Alternatives considered: Reusing `hot-top-n` as the core pool was rejected because `Hot` still behaves like a momentum-oriented platform ranking, even with an all-time window.

- Decision: Use these candidate signals for `core-pool` selection:
  - alphaXiv `Views + All time`
  - alphaXiv `Likes + All time`
  - alphaXiv `Comments + All time`
  - an external impact signal such as citation count
- Alternatives considered: alphaXiv-only ranking was rejected because it overfits platform-local behavior and underserves historically important but less socially active papers.

- Decision: Allocate core-pool category quotas using arXiv-led distribution, corrected by alphaXiv availability, with a minimum floor of 50 papers per included major category.
- Alternatives considered: equal quotas were rejected because they distort the real field mix; pure proportional allocation was rejected because it can erase the most important papers in lower-volume fields.

- Decision: Exclude very recent papers from the evergreen core pool by default so it does not duplicate daily ingestion work.
- Alternatives considered: allowing the newest papers into the core pool was rejected because `daily_new` and `daily_hot` already serve that freshness use case better.

- Decision: Store source artifacts under `backend/arxiv_id/` and auto-create missing directories.
- Alternatives considered: Keeping outputs under `alphaxiv/` was rejected because the server workflow already expects source state under `backend/arxiv_id/`.

- Decision: Write both Markdown and JSON for every export.
- Alternatives considered: Markdown-only output was rejected because downstream automation needs a structured machine-readable format.

- Decision: Keep source artifacts as fixed `latest.json` and `latest.md` files per source directory.
- Alternatives considered: Timestamped snapshots were rejected for this workflow because server-side scheduled jobs should update the current source view in place.

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
   - multi-source candidate expansion for `core-pool`
3. The script normalizes each record to a shared schema keyed by `arxiv_id`.
4. The script removes invalid IDs and de-duplicates within the run.
5. For `core-pool`, the script enriches records with category and impact metadata, applies quota-aware selection, and emits score metadata.
6. The script writes both JSON and Markdown outputs into the matching `backend/arxiv_id/<subdir>/` location.
6. Downstream automation can merge these artifacts with the rule set:
   - translate `hot` papers first
   - skip translation when the paper is already translated
   - still keep the source occurrence available for ranking, display, or audit
   - use `core-pool` as the long-lived pretranslation seed set rather than a daily queue

## Core Pool Selection Strategy
The first implementation should target a practical "best available" core pool rather than a mathematically perfect measure of universal importance.

### Target Size
- Total pool size: `4000`

### Candidate Expansion
- Pull ranked candidates from:
  - alphaXiv `Views + All time`
  - alphaXiv `Likes + All time`
  - alphaXiv `Comments + All time`
- Pull external impact metadata where possible, primarily citation counts
- Union candidates by `arxiv_id`

### Freshness Guard
- Exclude papers newer than the configured recency cutoff from the evergreen pool
- Default cutoff: 90 days
- Use a 2017-inclusive rolling lookback window by default so late-2010s landmark arXiv papers remain eligible

### Category Allocation
- Use arXiv-led category proportions as the primary quota baseline
- Use alphaXiv availability and engagement as a secondary correction signal
- Guarantee a minimum floor of 50 papers per included major category

### Intra-Category Ranking
- Rank papers inside each category using a blended score from:
  - long-window views
  - likes
  - comments
  - citation count
- Reserve a citation-anchor slice inside each category so highly cited landmark papers are retained even when platform engagement is weaker than newer momentum papers
- Export score breakdowns for auditability and later tuning

## Output Shape
Each JSON entry should include at least:

- `arxiv_id`
- `title`
- `source_mode`
- `source_rank` when applicable
- `primary_category` when available
- `publication_date`
- `updated_at`
- `source_url`
- `exported_at`

The Markdown view should be a readable projection of the same dataset.

Core-pool entries should additionally include:

- `score`
- `score_breakdown`
- `views_count`
- `vote_count`
- `signal_ranks`
- `selection_bucket` or equivalent quota metadata
- `selected_reason`

## Risks / Trade-offs
- alphaXiv feed responses contain malformed or non-paper IDs, so the script must validate IDs before output.
- alphaXiv and arXiv use different timestamps and freshness semantics, so the script must document which source field is used for filtering.
- The script can prepare source artifacts and de-duplication hints, but actual "already translated" checks may still depend on downstream systems not changed here.
- External impact APIs may have rate limits or partial coverage, so the first core-pool version should tolerate missing citation metadata instead of failing the whole export.
- Category balancing can become contentious when papers span multiple subjects, so the initial version should pick and document one stable primary-category rule.

## Migration Plan
1. Update the existing source-feed change to cover daily feeds and the core pool.
2. Update the export script to support mode-based hot and new exports.
3. Add a `core-pool` builder and write outputs into `backend/arxiv_id/core_pool/`.
4. Verify the script can generate the expected hot, new, and core-pool artifacts without duplicate IDs in a single export.

## Open Questions
- Which external impact provider should be the default first implementation if multiple public citation sources remain viable.

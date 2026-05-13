## Context
The current `hot` homepage tab is already wired through the frontend and backend, but its backend semantics are still internal `view_count` sorting. That is a reasonable local engagement view for already-published papers, but it does not answer the upstream question: which arXiv papers are broadly worth translating before our own users have interacted with them?

The repository already has a source-export foundation under `paper-source-feed-export`, and `scripts/export_alphaxiv_catalog.py` already knows about alphaXiv, arXiv, and OpenAlex. This design evolves that workflow into a scientifically grounded, auditable hot-ranking system instead of creating a separate ingestion path.

## Goals / Non-Goals
- Goals:
  - Build a multi-source ranking design that can justify why each paper appears in `Hot`.
  - Support publication-date windows matching the expected UI: `3 Days`, `7 Days`, `30 Days`, `90 Days`, and `All time`.
  - Keep `arxiv_id` as the canonical identity.
  - Export both machine-readable and human-readable ranked artifacts for operator review.
  - Feed later admin curation or content-pool prewarming without automatically translating every discovered paper.
  - Make homepage filtering feel close to the alphaXiv reference: a filter icon beside sort tabs, an active date pill, and a compact popover for publication-date choices.
- Non-Goals:
  - Implement the ranking workflow in this documentation-only change.
  - Scrape private, paid, or fragile sites as required dependencies.
  - Replace the existing admin curation quality gates.
  - Expand community intake beyond arXiv IDs or uploaded archives.
  - Claim arXiv exposes a first-party per-paper popularity leaderboard.

## Source Investigation
### Recommended source tiers
- Tier 0 canonical identity and freshness: arXiv API. Use it for `arxiv_id`, title, authors, categories, publication date, and freshness windows. arXiv supports API query sorting such as submitted date, but it is not a complete public per-paper hotness source.
- Tier 1 platform momentum: alphaXiv. Use its public feed endpoint for `Hot`, `Views`, `Likes`, and `Comments` across supported time intervals. A live probe on 2026-05-13 returned paper records with visit counts, votes, topics, GitHub URLs, and `github_stars` for `sort=Hot&interval=90 Days`.
- Tier 1 field-specific momentum: Hugging Face Papers. Treat as valuable for AI/ML papers when accessible, especially daily/trending paper signals, upvotes, and linked repos. Because direct endpoint access can be unstable from some environments, the adapter should be optional and fail-soft.
- Tier 2 scholarly impact: OpenAlex. Use arXiv DOI filters such as `10.48550/arxiv.*`, `cited_by_count`, publication date, topics, and field metadata. A live probe on 2026-05-13 returned arXiv DOI works and citation counts.
- Tier 2 scholarly impact fallback: Semantic Scholar Graph API. Use `externalIds.ArXiv`, `citationCount`, `influentialCitationCount`, fields of study, and paper metadata when coverage is available.
- Tier 3 reproducibility and engineering uptake: GitHub repository search, linked GitHub URLs from alphaXiv/Hugging Face, and Papers-with-Code style repository metadata. These signals should be capped and normalized because they overrepresent CS/AI papers.
- Tier 3 conference/review context: OpenReview for selected ML venues. Use as a contextual quality or acceptance signal, not as a global popularity source.
- Tier 4 early buzz: Reddit, Hacker News, blogs, and social mentions. These can help detect sudden attention but should remain low weight until rate limits, moderation noise, and field bias are controlled.

### Sources to avoid as primary dependencies
- Google Scholar: no official public API suitable for this use case.
- X/Twitter: access and terms are unstable for a core ranking dependency.
- Crossref Event Data: not a good new dependency because Crossref announced the Event Data service sunset for April 2026.
- Connected Papers, ResearchRabbit, Elicit, Litmaps, and similar discovery products: useful product references but not primary machine sources unless an approved API/license exists.
- bioRxiv, medRxiv, PubMed, and conference portals: useful for future non-arXiv intake, but out of scope for the current arXiv-ID admin curation flow unless they expose arXiv IDs or we expand intake identity rules.

## Ranking Model
### Candidate generation
For each requested window (`3d`, `7d`, `30d`, `90d`, `all`):
1. Query arXiv for canonical metadata and all new submissions in the window when the window is finite.
2. Query alphaXiv feed variants for the matching interval or nearest supported interval: `Hot`, `Views`, `Likes`, `Comments`.
3. Optionally query Hugging Face Papers for AI/ML momentum.
4. Enrich the union by `arxiv_id` with OpenAlex and Semantic Scholar impact metadata.
5. Enrich linked repositories from alphaXiv/Hugging Face/Papers-with-Code style sources with capped GitHub metrics.
6. Drop invalid IDs, withdrawn records, already failed permanently by intake policy, and entries outside the requested publication-date window.

### Score components
Use source-local percentile ranks and reciprocal-rank style features before blending. Raw counts must be log-scaled and winsorized so a single platform cannot dominate.

Recommended first-pass score:

```text
external_hot_score =
  0.30 * platform_momentum
+ 0.20 * cross_source_consensus
+ 0.18 * age_normalized_scholarly_impact
+ 0.12 * freshness_fit
+ 0.10 * reproducibility_signal
+ 0.06 * topic_quality_and_diversity
+ 0.04 * operator_policy_boost
```

Component definitions:
- `platform_momentum`: alphaXiv hot/views/likes/comments and optional Hugging Face trend/upvote ranks inside the selected window.
- `cross_source_consensus`: reward papers appearing in multiple independent source families; cap this so source-count gaming does not dominate.
- `age_normalized_scholarly_impact`: OpenAlex/Semantic Scholar citations compared to papers of similar age and broad category. For finite recent windows, this is a quality prior rather than the main driver.
- `freshness_fit`: favors papers whose arXiv publication date is well aligned with the selected window; avoids letting old citation classics dominate short-window `Hot`.
- `reproducibility_signal`: linked code repositories, stars, and recent activity, capped by category so CS papers do not crowd out all other fields.
- `topic_quality_and_diversity`: category balancing and field coverage guardrails.
- `operator_policy_boost`: small configurable boost for strategic categories or product goals; default `0`.

### Confidence and evidence
Every ranked record should include:
- `score`
- `score_breakdown`
- `confidence`
- `source_evidence[]` with source name, signal type, source rank/count, URL, fetched time, and freshness window
- `arxiv_id`, title, authors, primary category, publication date, updated date
- `selected_reason` in operator-readable text
- `exclusion_reasons[]` when an item is filtered out

Confidence should increase with independent source agreement and decrease when the score depends on only one noisy source, missing canonical metadata, or stale enrichment.

### Homepage display ranking
For already-published community papers, the visible `Hot` feed should eventually blend the external score with local engagement:

```text
display_hot_score =
  0.60 * decayed_external_hot_score
+ 0.25 * local_engagement_score
+ 0.10 * translated_readiness_score
+ 0.05 * recency_tie_breaker
```

This keeps the homepage responsive to our users while preventing a paper with only internal clicks from claiming broad research-world significance.

## Time Filter Semantics
- `3 Days`, `7 Days`, `30 Days`, and `90 Days` filter by arXiv publication date, not by our publish date.
- `All time` removes publication-date eligibility limits but still uses age-normalized impact so older papers do not win only because they had more years to accumulate citations.
- The selected interval is part of the backend/cache key and the exported artifact path.
- Recommended artifact layout:
  - `backend/arxiv_id/hot_ranked/3d/latest.json`
  - `backend/arxiv_id/hot_ranked/7d/latest.json`
  - `backend/arxiv_id/hot_ranked/30d/latest.json`
  - `backend/arxiv_id/hot_ranked/90d/latest.json`
  - `backend/arxiv_id/hot_ranked/all/latest.json`
- The matching Markdown files should explain source weights and list top candidates with score breakdown summaries.

## UI Design
The homepage browse controls should retain the existing sort tabs while adding a filter affordance inspired by the provided alphaXiv reference.

### Desktop
- Add an icon-only filter button immediately to the left of the segmented sort control.
- The active sort remains `Hot`, `Latest`, `Views`, and `Likes`.
- When a publication-date filter is active, show a compact pill near the controls, such as `90 Days x`; activating `x` resets to the default window.
- Clicking the filter icon opens an anchored popover below the button.
- Popover content:
  - Search input placeholder for future topic/category filtering.
  - A `Publication Date` group with rows: `3 Days`, `7 Days`, `30 Days`, `90 Days`, `All time`.
  - Current row shows selected state.
  - Selecting a row updates the window and refreshes the feed.
- First version may keep topic search visually present but functionally limited to category/topic filter only if the backend supports it; otherwise the search input should be omitted until usable.

### Mobile
- Use the same filter button, but open a bottom sheet instead of a narrow popover.
- Keep sort tabs and active filter pill from wrapping into overlapping rows.
- The bottom sheet should expose the same publication-date options and close after a selection.

### Default
Use `90 Days` as the default `Hot` window for the homepage. It is broad enough to avoid a purely same-day feed and fresh enough to avoid becoming an evergreen citation list.

## Data Flow
1. A scheduled or operator-triggered job builds ranked hot artifacts per configured window.
2. Each adapter fetches its source, normalizes by `arxiv_id`, and writes source evidence.
3. The ranker computes score, confidence, and reasons.
4. Operators review `latest.md` or admin UI candidate lists.
5. Approved candidates are submitted through existing admin arXiv curation in bounded batches.
6. Published papers enter the public community feed.
7. The homepage `Hot` tab requests the selected time window and shows published papers ordered by display hot score when available, otherwise by the current compatible fallback.

## Risks / Trade-offs
- alphaXiv is valuable but platform-local; it must not be the only signal if the goal is scientific credibility.
- Citation sources lag new papers; for short windows they should be quality priors, not the primary momentum signal.
- Hugging Face, GitHub, and Papers-with-Code style signals overrepresent AI/CS; category caps and diversity guards are required.
- Some APIs are rate-limited or partially unavailable; adapters must fail-soft and preserve audit evidence for missing sources.
- A visible filter popover can crowd the homepage controls; the active pill and mobile sheet must be responsive and compact.
- Cross-source aggregation is explainable but not perfectly objective; exposing breakdowns is part of the product contract.

## Migration Plan
1. Create the OpenSpec proposal and requirements for multi-source hot ranking and time-windowed filtering.
2. Later implementation should extend the existing source-export script or split it into reusable source adapters plus a ranking entrypoint.
3. Add tests around source normalization, scoring stability, interval filtering, and artifact generation.
4. Add backend API/cache support for `hotWindow`.
5. Add frontend filter controls and responsive popover/sheet behavior.
6. Add operator documentation for source weights and curation review.

## External References Checked
- arXiv API User Manual: https://info.arxiv.org/help/api/user-manual.html
- arXiv Statistics FAQ: https://info.arxiv.org/help/faq/statfaq.html
- OpenAlex Works API: https://docs.openalex.org/api-entities/works
- OpenAlex Work object: https://docs.openalex.org/api-entities/works/work-object
- Semantic Scholar API: https://www.semanticscholar.org/product/api
- Semantic Scholar Graph API docs: https://api.semanticscholar.org/api-docs/graph
- Hugging Face Hub API docs: https://huggingface.co/docs/hub/main/api
- GitHub REST search docs: https://docs.github.com/en/rest/search/search
- OpenReview API docs: https://docs.openreview.net/
- Crossref Event Data service page: https://www.crossref.org/services/event-data/

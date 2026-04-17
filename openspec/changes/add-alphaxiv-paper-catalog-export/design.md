## Context
alphaXiv exposes a sitemap index at `https://www.alphaxiv.org/sitemaps/sitemap-index.xml` that points to paper sitemap shards. The paper sitemaps include stable `/abs/<arxiv_id>` URLs, plus some non-primary `/abs/<id>/...` routes that should be ignored for the export.

## Goals / Non-Goals
- Goals:
- Enumerate the full set of paper URLs published in alphaXiv paper sitemaps
- Export a Markdown file containing the full de-duplicated arXiv ID set
- Keep the script standalone and runnable from the repository root
- Non-Goals:
- Persist paper metadata into the backend database
- Crawl comments, organizations, summaries, or authenticated content
- Build an incremental sync service

## Decisions
- Decision: Use the public sitemap index as the primary discovery mechanism.
- Alternatives considered: Recursive site crawling was rejected because it can miss papers and adds duplicate-discovery complexity. Reverse-engineering internal APIs was rejected because the observed endpoints rely on internal UUIDs and are less stable than sitemaps.
- Decision: Default to sitemap-only ID export instead of fetching every paper title.
- Alternatives considered: Fetching millions of paper pages to resolve titles was rejected for the default path because alphaXiv currently exposes about three million primary paper URLs, making full title hydration too slow for a routine export. A slower optional title mode can remain available for bounded runs.
- Decision: Write one Markdown export file under `alphaxiv/`.
- Alternatives considered: JSON output was rejected because the user explicitly requested Markdown.

## Risks / Trade-offs
- The sitemap export only guarantees a complete ID set by default, not complete title hydration.
- alphaXiv may change sitemap layout in the future, so the script should validate expected URL patterns and fail loudly when discovery breaks.
- Some sitemap shards contain malformed XML or non-primary `/abs/<id>/...` routes, so the parser needs tolerant extraction and strict route filtering.

## Migration Plan
1. Add the export script under `scripts/`.
2. Create `alphaxiv/` output if missing.
3. Run the script to generate the initial Markdown export of all discovered arXiv IDs.

## Open Questions
- None for the approved first version.

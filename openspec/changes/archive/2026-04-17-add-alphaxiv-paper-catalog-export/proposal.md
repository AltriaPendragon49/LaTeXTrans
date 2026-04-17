# Change: add alphaXiv paper catalog export

## Why
The repository needs a repeatable way to enumerate the papers indexed by alphaXiv and export a stable Markdown artifact containing paper titles and arXiv IDs.

## What Changes
- Add a Python script that reads the alphaXiv sitemap index and paper sitemaps
- Extract the canonical arXiv ID from each primary `/abs/<id>` paper URL
- Write a Markdown export under `alphaxiv/` with one entry per paper ID
- Keep title fetching as an optional slow path instead of a default requirement

## Impact
- Affected specs: `alphaxiv-paper-catalog-export`
- Affected code: `scripts/`, `alphaxiv/`

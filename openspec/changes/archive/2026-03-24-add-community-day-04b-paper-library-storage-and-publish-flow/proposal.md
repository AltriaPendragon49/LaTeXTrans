# Why
- Day 4 proved that a paper-centric read surface can exist, but it also exposed a structural gap: community papers still depend on task-owned output directories rather than a community-owned paper library.
- The current `/translate` workspace produces normal task results, yet those results do not reliably become community papers, which breaks the intended Week 1 paper-first chain.
- Day 5 is supposed to stabilize `submit -> paper detail -> translate -> preview/download`, so the missing library/publish layer must be inserted before Week 1 readiness can be trusted.

## What Changes
- Add a community-owned paper library storage layer under a dedicated relative data directory instead of directly reusing task output paths as the long-term community asset source.
- Auto-publish completed authenticated translation tasks into the community paper library when no stronger official paper already owns that slot.
- Reuse and upgrade existing community papers by syncing copied `source_archive`, `translated_pdf`, and `preview_html` assets into the paper library.
- Resolve preview/download reads through library-relative storage paths so the same deployment can be moved across servers without hardcoded absolute paths.
- Update the Week 1 execution ledger so this Day 04B change is explicit between Day 4 and Day 5.

## Impact
- Adds capability `community-paper-library-storage`.
- Depends on `add-community-day-04-paper-translation-preview-download`.
- Becomes a dependency of `add-community-day-05-week1-e2e-stabilization`.
- Touches backend community asset sync, translation-start publish watching, preview/download path resolution, storage config, and Week 1 planning docs.

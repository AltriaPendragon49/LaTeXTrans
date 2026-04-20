## Context
Public translated PDF reads currently do too much synchronous work at request time. The request path may repair missing translated assets, materialize PDFs from object storage into a temp directory, and trim leading blank pages before streaming the file. This creates a large latency gap between source and translated PDF reads and increases the chance of timeouts or transient failures.

## Goals
- Keep leading blank-page trimming mandatory for translated PDF delivery.
- Make public translated PDF preview and download reads lightweight and deterministic.
- Upgrade existing community papers in place instead of requiring full re-curation.

## Non-Goals
- Rework the source PDF path.
- Change the frontend reader contract.
- Remove all fallback recovery logic for non-public internal workflows.

## Decisions
- Decision: The trimmed translated PDF becomes the canonical public delivery artifact.
  - Why: The user-facing path should only serve a final artifact, not derive one on demand.
- Decision: Canonical delivery generation happens when translated assets are published or recovered into the community library.
  - Why: This preserves trimming while shifting the cost off the critical read path.
- Decision: Public preview and download resolution only serve an already-prepared canonical asset and do not trigger repair-time trimming.
  - Why: Request-time repair is the main source of cold-read latency and unpredictability.
- Decision: Existing papers are upgraded through a dedicated backfill script that rewrites the latest `translated_pdf` asset in place.
  - Why: The current repository model already supports latest-asset replacement, so a backfill is cheaper and safer than full re-ingestion.

## Alternatives Considered
- Keep request-time trimming and add more caches.
  - Rejected because first-read latency would still remain high and the failure surface would stay large.
- Remove blank-page trimming for public reads.
  - Rejected because trimmed delivery is a hard product requirement.
- Force full re-curation for all existing papers.
  - Rejected because the current asset model already allows in-place latest-asset replacement.

## Risks / Trade-offs
- Canonical asset generation moves more work into publish and recovery flows, so failures there need clear fallback logging.
- Backfill must avoid corrupting papers whose translated PDF is missing or unreadable; those papers should be skipped and reported instead of partially rewritten.

## Migration Plan
1. Update translated asset persistence so it stores a canonical trimmed delivery PDF during asset creation.
2. Update public translated preview/download reads to resolve only the canonical asset path or object-storage URL.
3. Add a backfill script that scans public papers, re-materializes the current translated asset if needed, regenerates the canonical trimmed PDF, and upserts the latest asset.
4. Run the backfill for existing papers after deployment and review the skipped-paper report.

## Open Questions
- None. The approved direction is to keep trimming mandatory and move it off the read path.

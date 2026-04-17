## Context
Ordinary tasks currently assume `source_path` and `output_path` refer to durable local filesystem directories under `backend/data/uploads` and `backend/data/outputs`. Community-paper flows already have an object-storage abstraction, but ordinary-task routes, task recovery, and download endpoints still read directly from local disk.

The approved direction is:
- COS is the durable source of truth for ordinary tasks
- Local disk is only temporary runtime cache
- Preview endpoints remain backend-proxied
- Download endpoints use signed COS delivery
- Existing API paths remain stable

## Goals
- Reuse the existing storage backend abstraction rather than introducing a second COS client path
- Keep task persistence records (`source_path`, `output_path`) meaningful across both local-disk and COS modes
- Support ordinary-task translation start, output reuse, preview, and downloads without requiring permanent local artifacts

## Non-Goals
- Backfilling or migrating historical ordinary-task local artifacts in this change
- Reworking community-paper storage flows
- Changing external endpoint paths or auth contracts

## Decisions
- Persist ordinary-task COS references as backend-relative logical paths such as `data/uploads/...` and `data/outputs/...`, while local-disk mode can continue to use local filesystem paths
- Add an ordinary-task storage helper that can:
  - upload directory trees to the configured storage backend
  - materialize stored directory trees into local runtime cache
  - build/read an output manifest for preview and signed-download resolution
- Persist a manifest into each stored output root so preview/download endpoints can resolve translated PDF, terminology CSV, logs, and translated-source archive without scanning local disk
- Keep runtime translation output rooted in the existing local `outputs_dir`, then sync to COS and clear that directory after durable persistence

## Risks / Trade-offs
- Output reuse in COS mode adds hydrate-and-repersist I/O instead of zero-copy local reuse
- Manifest drift could break downloads if output sync misses final files
- Some legacy local-disk-only recovery heuristics remain in the codebase and need careful branching so COS mode does not accidentally treat logical object paths as local directories

## Migration Plan
1. Add storage helper and backend capabilities for listing/downloading stored objects
2. Update ordinary-task upload/arXiv ingestion to sync sources to COS
3. Update translation/output-reuse to hydrate sources, sync terminal outputs, and clean local cache
4. Update preview/download endpoints to consume stored manifests and signed URLs
5. Verify focused unit tests in both helper and route layers

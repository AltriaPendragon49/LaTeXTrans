## Context
The current production deployment successfully completes translation and community publication for papers such as `2508.18791`, but browser clients still see `ERR_CONNECTION_CLOSED` against `https://api.latextrans.online`. Server-local verification shows the backend, Nginx, and generated assets are healthy. This indicates the main failure is in the external ingress path rather than in translation or asset generation.

At the same time, runtime uploads, outputs, and community paper assets still use server-local directories as the canonical store. That increases coupling to one host, keeps multi-megabyte files on the server, and encourages API payloads that are too large for fragile browser sessions.

## Goals / Non-Goals
- Goals:
  - Make production API ingress stable for browser clients by aligning runtime access with the Cloudflare-managed edge path.
  - Make COS the canonical production store for runtime artifacts and published community assets.
  - Keep production local disk ephemeral by treating it as a temporary cache only.
  - Preserve local development without COS through a local-disk fallback mode.
  - Reduce first-read fragility by making paper-detail responses lightweight and asset-addressable.
- Non-Goals:
  - Rewriting LaTeX compilation to run directly inside object storage without any local filesystem usage.
  - Removing all temporary local files during active task execution.
  - Backfilling every historical asset in the same change unless required for migration safety.

## Decisions
- Decision: Production ingress will use a Cloudflare-managed edge path rather than direct public browser access to the CVM origin TLS endpoint.
  - Why:
    - External browser and desktop clients fail during or before TLS response handling while server-local requests succeed.
    - The repository's infrastructure direction already favors Cloudflare-managed ingress.
  - Alternatives considered:
    - Keep direct public origin TLS and tune Nginx only.
      - Rejected because current evidence points to origin-facing external connection instability, not just a single API route bug.
    - Put a second reverse proxy in front of Nginx on the same host.
      - Rejected because it keeps the same stateful origin exposure and does not address repository drift from the intended ingress model.

- Decision: Introduce a unified storage backend abstraction with `local_disk` and `cos`.
  - Why:
    - The data model already has `paper_assets.storage_backend`, so the system has a natural extension point.
    - Production needs object storage durability, while local development must remain simple.
  - Alternatives considered:
    - Keep ad hoc path branching in paper services and download routes.
      - Rejected because storage behavior now affects uploads, outputs, previews, downloads, cleanup, and detail bootstrapping across multiple services.

- Decision: Production runtime artifacts will use local disk only as a temporary cache.
  - Why:
    - LaTeX compilation, preview generation, and source scanning still need a real filesystem.
    - The user wants the server to stop acting as the durable store.
  - Operational rule:
    - Source uploads, task outputs, preview HTML, translated PDFs, task logs, and other retained runtime artifacts are written locally first.
    - After a successful COS upload, the cached local copy is deleted unless it is still needed by the active task stage.
    - Cleanup failures are logged and retried through existing startup/admin reconciliation flows.

- Decision: Published community assets and retained runtime artifacts will store COS object keys as the canonical `file_path` when `storage_backend=object_storage`.
  - Why:
    - The current schema can already distinguish storage backend, so a bucket-relative object key can become the canonical reference without forcing an immediate schema expansion.
  - Consequence:
    - Storage resolution becomes backend-aware instead of assuming every `file_path` is a local filesystem path.

- Decision: Public paper-detail APIs will return lightweight reader bootstrap metadata instead of embedding large preview bodies directly in the main detail response.
  - Why:
    - Current detail responses can exceed 9 MB because they inline preview HTML and reader content.
    - That makes paper detail brittle when the network is even mildly unstable.
  - Consequence:
    - The detail response returns metadata, reader state, and asset locators.
    - The frontend fetches preview HTML or PDF resources through dedicated asset endpoints or signed object-storage URLs.

- Decision: Public/community asset delivery will support object-storage-native reads.
  - Why:
    - Production should not require the API host to keep every PDF and preview file on disk.
  - Consequence:
    - PDF/preview routes may return a short-lived signed URL, a redirect to COS, or a first-party proxy response depending on the asset class and frontend needs.
    - Local development keeps the current direct file-serving path.

## Risks / Trade-offs
- COS upload timing adds a new failure boundary after local generation.
  - Mitigation:
    - Promote only after upload success.
    - Keep retryable cleanup and reconciliation hooks.
- Signed URL or redirect flows can change frontend assumptions.
  - Mitigation:
    - Preserve stable route contracts while letting the backend choose local file serving vs object-storage delivery.
- Task recovery becomes more dependent on storage metadata correctness.
  - Mitigation:
    - Keep deterministic object-key conventions and add tests for restart recovery under both storage backends.
- Restoring Cloudflare-managed ingress touches deployment and DNS/runtime config, not just application code.
  - Mitigation:
    - Treat ingress cutover as a staged deployment task with health verification before traffic shift.

## Migration Plan
1. Add storage configuration for backend mode selection, COS bucket/prefix settings, and temporary local cache directories.
2. Implement backend storage abstraction and backend-aware path resolution.
3. Update runtime upload/output persistence so production uploads canonical artifacts to COS and clears cache after success.
4. Update community paper publication, preview, and download flows to read from `object_storage` assets.
5. Slim the paper-detail contract so it returns reader bootstrap metadata plus asset locators rather than large inline HTML payloads.
6. Update the frontend reader to load preview HTML/PDF from those locators.
7. Restore Cloudflare-managed ingress for `api.latextrans.online`, verify browser health from an external client, then remove the direct-origin browser dependency.
8. Validate local development without COS and production behavior with COS enabled.

## Open Questions
- Whether translated preview HTML should always be proxied through first-party API routes or can be loaded directly from signed COS URLs in all reader modes.
  - Initial recommendation:
    - Keep first-party preview routes for HTML reader safety and flexibility.
    - Allow PDF delivery to redirect to signed COS URLs when suitable.

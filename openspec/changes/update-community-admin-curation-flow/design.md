## Context
The repository currently treats the community homepage and paper detail page as public agent-aware surfaces, while authenticated tool translations can auto-publish fallback community papers. The requested product direction keeps the current page layouts mostly intact but changes what those pages do:

- community becomes a curated reading/search destination
- ordinary translation tools remain available but do not publish community content
- only admins can add or delete community papers
- public paper detail uses prepared structured insights instead of a live copilot pane

The project already has local-role admin support and a local/MySQL-backed auth/session model. We should reuse that instead of inventing a new admin account system.

## Goals / Non-Goals
- Goals:
  - Preserve the existing homepage and paper-detail visual shells as much as possible.
  - Replace public agent entry points with lower-cost curated reading and search behavior.
  - Limit homepage search to formal public community papers only.
  - Create a single official admin-only community ingestion path.
  - Ensure public community papers are only exposed after the full pipeline succeeds.
  - Support bounded-concurrency batch intake for both `arXiv ID` and archive uploads.
  - Keep a stable, non-changing canonical `paper_id` for each community paper.
  - Make community deletion a comprehensive hard delete.
- Non-Goals:
  - Do not redesign the entire site information architecture.
  - Do not build a self-serve admin-management console.
  - Do not delete the community-agent backend runtime or routes in this change.
  - Do not auto-publish ordinary user tool outputs into the community library.

## Decisions

### Decision: Community and tools become parallel but separated product surfaces
Community remains public-facing and curated. The tools hub continues to support normal user translation. Ordinary tool translations no longer auto-publish into community.

Why:
- It matches the requested product boundary.
- It avoids mixing personal translation experiments with public library content.
- It keeps the direct translation workflow available without forcing community publication.

### Decision: Homepage search is limited to formal public community papers
Homepage search only queries the formal public community library. It does not include:

- ordinary user translation-tool outputs
- incomplete or processing curation items
- deleted or deleting papers

Why:
- It preserves the requested boundary between community content and personal tool results.
- It prevents partially curated or soon-to-be-deleted records from leaking into the public product surface.

### Decision: Admin curation is the only community-publication path
Only the admin-only curation page may create new publicly visible community papers. A curated item must finish:

1. intake
2. metadata preparation
3. translation
4. structured insight generation
5. publication

Public visibility is granted only after all required stages succeed.

Why:
- It guarantees community papers are complete.
- It keeps half-finished content out of the public feed.
- It provides one clear operational path for official library growth.

### Decision: Canonical paper identity is stable and repeat curation overwrites in place
Every community paper has one stable internal `paper_id`. That `paper_id` is immutable once created. Repeat curation for the same canonical paper must reuse the same `paper_id` instead of creating a new one.

For canonical matches:
- `arXiv ID` intake reuses the canonical paper identified by that `arXiv ID`
- archive intake that later resolves to an already-known canonical paper reuses that same `paper_id`
- the latest successful admin curation run overwrites the previously published community-facing assets and metadata for that canonical paper

Why:
- It keeps detail routes, deletion, search, and references stable.
- It matches the requested “same community paper, latest result covers the old one” behavior.
- It avoids link churn and duplicate public records.

### Decision: Admin identity is granted operationally, not by password sharing
Admin creation is not a user-facing password workflow. The intended operational flow is:

1. the real user logs in normally
2. the local user record is created or reused
3. the user receives `admin` through existing local role mechanisms (seeded config or direct role row)

Why:
- The codebase already supports local role-based admin checks.
- It avoids handling raw passwords in development operations.
- It fits the existing `LOCAL_ADMIN_EXTERNAL_USER_IDS` and `user_roles` model.

### Decision: Structured insights are stored assets with a fixed schema
The detail-page right pane will read persisted structured insights instead of generating them live. The fixed section set is:

- `problem`
- `method`
- `key_idea`
- `experiment`
- `result`
- `limitation`

Each section stores language-aligned content for at least English and Chinese. The minimum section payload includes:

- `section_key`
- `summary_en`
- `summary_zh`
- `bullets_en[]`
- `bullets_zh[]`
- `body_en`
- `body_zh`
- `status`
- `updated_at`

The UI selects which language to display based on the current reader mode. If the required language variant is missing for a visible legacy/degraded paper, the pane shows an explicit not-ready placeholder rather than silently switching languages.

Current version rule:
- structured insights are system-generated and read-only in this version
- future admin editing remains an allowed extension, but it is not part of this version

Why:
- It produces stable, testable page output.
- It prevents layout drift caused by per-request generation.
- It aligns cleanly with the requested “follow the current reading mode” behavior.

### Decision: Archive-based intake must extract feed metadata before publication
When admins upload a TeX-containing archive, the curation pipeline must extract title and abstract so the resulting community card can render the same kind of headline metadata expected from arXiv-based intake.

Why:
- The homepage feed needs stable title/abstract cards regardless of intake source.
- Archive uploads otherwise produce weaker community presentation than arXiv intake.

### Decision: Batch ingestion uses bounded concurrency
Batch curation supports both multiple `arXiv ID`s and multiple archives. Submission enters a queue with controlled parallelism rather than pure serial execution or unconstrained fan-out.

Each batch item has its own lifecycle state. One failed item does not block the other items from finishing, and publication readiness is decided per paper, not per batch.

Why:
- The user explicitly wants speed improvements as long as final quality stays intact.
- Bounded parallelism is the safest way to reuse the translation kernel without overloading the system.

### Decision: Public agent entry points are hidden and direct product access is disabled
Homepage agent composer, paper-detail public copilot pane, and sidebar agent affordances are hidden from normal product flows. The retained community-agent code and runtime remain in the repository for future recovery, but the current product state does not allow direct access for ordinary users or admins.

Why:
- The request is explicit that code/services must remain.
- This keeps a future reactivation path open without requiring runtime recreation.
- It better satisfies the cost-reduction goal than hiding UI alone.

### Decision: Community deletion is a true hard delete executed by a persistent async worker
Admin delete removes:

- the canonical paper row
- related local paper-facing rows (assets, reactions, structured insights, related task links, etc.)
- source archives, extracted work directories, preview HTML, translated HTML/PDF, thumbnails, and the paper’s local community asset directory
- related search/cache/index entries

Delete semantics:
- the paper becomes immediately invisible to homepage feed, search, and detail routes as soon as delete is accepted
- the actual hard delete runs asynchronously in the background
- the delete job is persisted
- if cleanup fails at any step, the system keeps retrying automatically until hard delete completes
- restart must resume unfinished delete jobs

Why:
- The requested use case is to remove bad or unwanted papers cleanly.
- Immediate public invisibility avoids front-end clutter.
- Persistent retries make the hard-delete promise realistic even when cleanup spans many resources.

## Risks / Trade-offs
- Structured insight generation adds another quality-sensitive generation stage.
  - Mitigation: fixed schema, bounded output size, publication gate only after success.
- Archive metadata extraction may be less reliable than arXiv metadata.
  - Mitigation: extract from TeX sources before publication and keep a failure path that blocks public release until required metadata exists.
- Hidden-but-retained agent code can drift if not documented.
  - Mitigation: record retained routes/services explicitly in the change and keep tests around hidden UI behavior.
- Hard delete removes recovery convenience.
  - Mitigation: restrict to admins and make the contract explicit.
- Canonical archive-to-paper matching can be ambiguous when no arXiv identifier is present.
  - Mitigation: require stable dedupe logic and always preserve the first canonical `paper_id` once chosen.

## Migration Plan
1. Introduce admin-only curation APIs, structured insight persistence, and hard-delete flow.
2. Stop ordinary tool translation auto-publication.
3. Update homepage and detail UI to hide public agent entry points and surface search/insights instead.
4. Add admin-only sidebar entry and curation page.
5. Verify normal user tools remain available and do not publish community content.

## Open Questions
- What exact archive dedupe heuristic should determine that a no-arXiv archive matches an existing canonical paper before in-place overwrite is allowed?
- What retry interval/backoff policy should the persistent hard-delete worker use while still satisfying the “retry until complete” contract?

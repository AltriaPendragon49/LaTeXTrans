## Context
The repository currently treats the community homepage and paper detail page as public agent-aware surfaces, while authenticated tool translations can auto-publish fallback community papers. The requested product direction keeps the current page layouts mostly intact but changes what those pages do:

- community becomes a curated reading/search destination
- ordinary translation tools remain available but do not publish community content
- only admins can add or delete community papers
- public paper detail uses prepared paper-guide modules instead of a live copilot pane

The previous implementation direction moved from legacy summary/body/bullets storage to a six-module content-only guide. After content review, that six-module shape is still too diffuse and repetitive. The desired product now converges on a higher-density five-module reading guide.

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
  - Turn the detail-page guide into a fixed five-module Chinese paper-guide system optimized for reader understanding.
- Non-Goals:
  - Do not redesign the entire site information architecture.
  - Do not build a self-serve admin-management console.
  - Do not delete the community-agent backend runtime or routes in this change.
  - Do not auto-publish ordinary user tool outputs into the community library.
  - Do not migrate or backfill old public papers into the new five-module shape in this change.

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
4. paper-guide generation
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

### Decision: Paper guides become a fixed five-module Chinese paper-guide system
The detail-page right pane will read persisted paper-guide content instead of generating live copilot output. The system, not the model, owns the structure. The fixed five modules are:

- `problem`: 这篇论文解决什么问题，为什么重要，现有方法的关键不足是什么？
- `solution`: 作者的核心思路是什么，方法整体是如何工作的？
- `innovation`: 论文的关键创新点有哪些，相比已有方法，本质区别在哪里？
- `experiment`: 论文如何验证方法有效性，主要结论是什么？
- `future`: 这项工作有什么潜在改进或扩展方向，对相关研究有哪些启发？

Each module stores reader-facing Chinese text in a system-owned object. The persisted contract remains intentionally minimal:

- `guide_sections.problem.content`
- `guide_sections.solution.content`
- `guide_sections.innovation.content`
- `guide_sections.experiment.content`
- `guide_sections.future.content`

A representative stored shape is:

```json
{
  "paper_id": "...",
  "guide_sections": {
    "problem": { "content": "..." },
    "solution": { "content": "..." },
    "innovation": { "content": "..." },
    "experiment": { "content": "..." },
    "future": { "content": "..." }
  }
}
```

Reader-mode switches still control the paper reader itself, but they do not change the guide language. Legacy papers are out of scope for this refinement: the new five-module guide is guaranteed only for newly curated papers after this change lands.

Why:
- The intended reading path is now problem -> method -> innovation -> experiment -> outlook.
- Five modules reduce repetition and make module boundaries clearer than the previous six-module shape.
- The final UI only needs one Chinese text block per module.

### Decision: Each module is generated independently from title + abstract + module-relevant excerpts
Paper-guide generation runs after translation succeeds. The backend prepares module-specific source material from the translated paper, then asks the model to answer one fixed question at a time.

Preferred source emphasis by module:

- `problem`: title + abstract + introduction + nearby current-method limitation paragraphs
- `solution`: title + abstract + method / system overview
- `innovation`: title + abstract + contribution paragraphs + key method-design paragraphs
- `experiment`: title + abstract + experiment / evaluation / results
- `future`: title + abstract + conclusion / discussion / limitation

Fallback routing rule:
- if exact section labels are missing, use the nearest translated sections in reading order
- do not use one shared full-paper payload for all modules as the normal path

Generation rule:
- five independent LLM calls
- one module per call
- no requirement that the model returns a multi-section package

Why:
- single-module retries are much safer than whole-package retries
- title + abstract act as the shared semantic anchor for every module
- prompt tuning becomes simpler and more targeted

### Decision: Model outputs plain Chinese text, not strict JSON contracts
The model should only produce the Chinese content body for one module. The system wraps that content into the fixed module object structure.

Prompt-level requirements:
- answer in Chinese
- explain clearly for readers
- ground the answer in the provided paper content
- allow normal prose and paragraphs
- do not output JSON
- do not output headings or numbering
- keep the answer focused on the current question instead of summarizing the whole paper
- prefer paper-specific details over generic praise

Per-module boundary rules:
- `problem` answers what the paper solves, why it matters, and where prior approaches fall short
- `solution` answers how the method works
- `innovation` answers what is fundamentally new compared with prior work
- `experiment` answers how the paper validates effectiveness and what the results show
- `future` answers realistic extensions, limits, and research implications

Acceptance rule for each module:
- `guide_sections.<key>.content` must be non-empty after normalization
- `guide_sections.<key>.content` must pass a minimum readability check, including:
  - minimum content length after trimming
  - rejection of obvious failure placeholders
  - rejection of exact duplicates across modules

Why:
- strict JSON parsing and repair loops created instability without product value
- the frontend only consumes display text
- system-controlled structure removes an entire failure class

### Decision: Publication still gates on five modules, but fallback content is allowed
Admin publication still requires all five modules to exist before the paper becomes public. However, a module should not block publication solely because a high-fidelity LLM answer failed in one attempt.

Fallback rule:
- retry the failed module a bounded number of times
- if it still fails, generate a simplified Chinese fallback from trusted inputs such as title + abstract plus a small module-relevant excerpt when available
- store that fallback inside the module object as `content`
- the fallback path MUST guarantee that the final stored value is a displayable Chinese body paragraph rather than another failure marker or retry envelope

Why:
- five-module completion remains a product gate
- LLM volatility should not deadlock the publish path
- the user explicitly prefers robustness over fragile structure

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
- Paper-guide generation adds another quality-sensitive generation stage.
  - Mitigation: fixed module set, module-specific prompts, independent retries, title/abstract anchoring, and fallback content.
- Archive metadata extraction may be less reliable than arXiv metadata.
  - Mitigation: extract from TeX sources before publication and keep a failure path that blocks public release until required metadata exists.
- Hidden-but-retained agent code can drift if not documented.
  - Mitigation: record retained routes/services explicitly in the change and keep tests around hidden UI behavior.
- Hard delete removes recovery convenience.
  - Mitigation: restrict to admins and make the contract explicit.
- Canonical archive-to-paper matching can be ambiguous when no arXiv identifier is present.
  - Mitigation: require stable dedupe logic and always preserve the first canonical `paper_id` once chosen.
- Local excerpt routing can misclassify sections on papers with weak headings.
  - Mitigation: use title + abstract as the shared anchor and fall back to reading-order heuristics.

## Migration Plan
1. Keep the existing admin-only curation APIs, hard-delete flow, and community/tool separation.
2. Replace the six-module guide contract with the final five-module paper-guide contract.
3. Rework module source extraction, prompting, validation, and fallback around the new five-module reading path.
4. Update the detail UI to render the fixed five-module guide only.
5. Validate with a real admin curation rerun for `2508.18791` after deleting its old stored guide artifacts.

## Open Questions
- What exact archive dedupe heuristic should determine that a no-arXiv archive matches an existing canonical paper before in-place overwrite is allowed?
- What retry interval/backoff policy should the persistent hard-delete worker use while still satisfying the “retry until complete” contract?

## Context
The production examples show two distinct failure classes:

- API pressure or upstream failures can result in source text being returned as fallback and later published as if translation succeeded.
- Structure rescue paths can emit fixed Chinese placeholders such as `相关内容已转为简要中文表述`, which are Chinese-looking but semantically useless.

The old system ran section-level concurrency but translated child environments and captions sequentially inside a section. The new path adds section-internal `asyncio.gather()` and a global/default LLM concurrency around 10, which can multiply outbound requests from one paper and hammer a single key or relay. The existing token pool is mainly a failover layer after 429/503 rather than a pre-flight scheduler.

## Goals
- Support the current one-key server safely.
- Support future three-key production where keys are independent accounts with independent quotas.
- Prefer two simultaneous translation tasks when three healthy independent keys exist, leaving one member as reserve.
- Keep one task mostly bound to one key so a task does not spread pressure across every key by default.
- Remove fake fallback from user-visible production outputs.
- Keep community publish gates strong enough to block unusable papers without rejecting healthy translated papers for citations, terminology, math, references, or short unavoidable source fallback.

## Non-Goals
- Do not require distributed rate limiting in the first implementation if production runs one backend worker process.
- Do not make the fallback a general perfect LaTeX repair engine.
- Do not block normal user preview/download behavior solely because community publishing is stricter.

## Decisions
- Decision: introduce a `LlmMemberScheduler` in front of every outbound LLM call.
  - Each configured member has `member_id`, `base_url`, masked key, optional `account_id`, `quota_scope`, per-member concurrency/RPM/TPM settings, cooldown state, and circuit-breaker state.
  - Each base or relay may also have a shared pool limiter. Multiple keys on the same relay are treated as shared unless configured as independent accounts.
- Decision: bind each translation task to a primary member lease.
  - First-pass section/env/caption calls prefer the task primary member.
  - Failover is allowed only after bounded cooldown/fatal classification, and must be recorded.
  - With three healthy independent members, community production may run two tasks concurrently and reserve one member for failover/spikes.
  - With one configured member, community production runs one active translation task by default.
- Decision: remove section-internal parallel translation as the default behavior.
  - Section-level concurrency remains configurable and bounded by the scheduler.
  - Environment and caption translation inside one section is sequential by default to reduce burstiness and preserve locality.
- Decision: fixed Chinese fallback text is forbidden in final community output.
  - It may exist only as an internal diagnostic sentinel if needed, and any sentinel reaching final preview/PDF blocks publish.
- Decision: structural fallback is semantic and minimal.
  - If structured LaTeX preservation fails, the pipeline may extract prose units, translate them as plain text, and rebuild with minimal safe LaTeX paragraphs while preserving essential section titles and non-translatable blocks.
  - API failure never uses this path unless a real translation response was obtained.
- Decision: community publishing uses a separate quality gate from ordinary task completion.
  - A task may finish for debugging/user download, but community canonical asset sync must pass the production gate.

## Quality Gate Policy
- Hard fail:
  - Any fixed fake fallback phrase in final text/PDF/preview.
  - Multiple source fallback sections.
  - One source fallback section that is long, important, or dominates natural-language body text.
  - High English prose retention in abstract/introduction/conclusion or across the document.
  - Fatal upstream provider state such as authentication failure, quota exhaustion, or unsupported model.
- Tolerate:
  - Citations, references, author names, affiliations, code/verbatim, URLs, formulas, command names, dataset/model names, acronyms, and technical English terms.
  - At most one short source fallback section, configurable, defaulting to a small absolute limit and a small percentage of body text.

## Rollout
1. Stopgap config/code changes: disable section-internal gather, reduce community task concurrency in one-key mode, block fake fallback from publish.
2. Scheduler: route all LLM calls through member leasing and per-member/pool limiters.
3. Semantic fallback: replace fake downgrade and oversize source passthrough with minimal plain-Chinese fallback where possible.
4. Production gate: enforce before community asset sync, emit machine-readable diagnostics, and build a backfill scanner for existing community papers.

## Risks
- Too strict a gate could reject usable papers. Mitigation: make thresholds configurable, ignore known non-prose regions, and produce diagnostics before hard failing.
- Too loose a gate could still publish bad outputs. Mitigation: fixed fake fallback and multi-section source passthrough are non-negotiable hard failures.
- Independent-account assumptions could be configured incorrectly. Mitigation: default same-base members to shared quota unless explicitly marked independent.

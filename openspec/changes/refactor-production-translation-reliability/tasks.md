## 1. Scheduler and Admission
- [ ] 1.1 Add runtime config for LLM members: `member_id`, `base_url`, API key, optional `account_id`, `quota_scope`, per-member concurrency/RPM/TPM, pool shared limits, reserve count, and community task policy.
- [ ] 1.2 Implement a central LLM scheduler that leases a primary member per translation task and gates every outbound LLM call before HTTP dispatch.
- [ ] 1.3 Add single-key and multi-independent-account policies: one active community task for one member; two active community tasks with three healthy independent members and one reserve by default.
- [ ] 1.4 Classify provider failures into retryable rate-limit, retryable transient, member cooldown, pool cooldown, and fatal upstream errors.
- [ ] 1.5 Persist masked scheduler decisions, member lease IDs, cooldown/failover events, and effective concurrency in task logs.

## 2. Translation Concurrency
- [ ] 2.1 Remove or disable section-internal `asyncio.gather()` for environment/caption translation in the community production path.
- [ ] 2.2 Make section-level concurrency explicit and scheduler-aware; default community production to conservative section concurrency without nested fan-out.
- [ ] 2.3 Ensure all section, environment, caption, repair, rescue, diagnostic, and structured-insight calls use the scheduler entrypoint.
- [ ] 2.4 Add regression tests proving environment/caption translation inside a section is sequential by default.

## 3. Fallback and Downgrade
- [ ] 3.1 Remove fixed fake Chinese fallback text from final translation paths.
- [ ] 3.2 Change API failure fallback so source text is not marked as translated success; record explicit provider failure status instead.
- [ ] 3.3 Implement semantic minimal-LaTeX fallback for structure failures after real model translation is available.
- [ ] 3.4 Replace oversize source passthrough for prose chunks with safe chunk splitting or semantic fallback where possible.
- [ ] 3.5 Add tests for fake fallback blocking, source passthrough metadata, and semantic fallback output.

## 4. Community Production Gate
- [ ] 4.1 Add a community publish quality gate that evaluates final preview/text and task metadata before canonical asset sync.
- [ ] 4.2 Hard-fail fake fallback phrases, excessive source fallback, large English prose retention, and fatal upstream provider states.
- [ ] 4.3 Tolerate citations, bibliography, code/verbatim, URLs, formulas, acronyms, proper nouns, and one short source fallback section under configurable thresholds.
- [ ] 4.4 Emit machine-readable gate diagnostics and keep failed artifacts for operator debugging without publishing them as healthy community assets.
- [ ] 4.5 Add a backfill scanner for existing `backend/data/community_papers` assets to flag or requeue bad papers.

## 5. Verification
- [ ] 5.1 Add unit tests for scheduler member selection, reserve behavior, cooldown, and failover.
- [ ] 5.2 Add integration-style tests for one-key and three-independent-key production policies.
- [ ] 5.3 Add regression tests using known bad patterns from `1712.01815`, `1804.03999`, `2111.14330`, `2112.10752`, and `2203.03605`.
- [ ] 5.4 Run existing backend translation tests and OpenSpec validation.

## 1. Structured Insight Source Packets
- [x] 1.1 Extend the runtime structured-insight source loader so each section can carry normalized original-source text and translated text from `sections_map.json`.
- [x] 1.2 Update module source composition to prefer hybrid runtime artifacts and keep preview HTML only as a degraded fallback.

## 2. Structured Insight Parallel Generation
- [x] 2.1 Convert five-module generation to a parallel first pass.
- [x] 2.2 Add targeted repair so only invalid, unreadable, or duplicated modules are retried after the first pass.
- [x] 2.3 Preserve Chinese-only readable fallback content for modules that still fail after bounded repair.

## 3. Structured Insight Token-Pool Routing
- [x] 3.1 Add member-level `503` handling with a longer cooldown than the current one-second behavior.
- [x] 3.2 Add structured-insight task-local `base_url` preference shifting after cumulative three `503` responses on the same base.
- [x] 3.3 Preserve current-member retry when every member is unavailable and avoid global base bans.

## 4. Verification
- [x] 4.1 Add or update unit tests for hybrid source assembly, parallel generation, targeted repair, task-local base preference, and longer `503` cooldown behavior.
- [x] 4.2 Validate the OpenSpec change with `openspec validate update-structured-insight-base-failover-and-ast-sourcing --strict --no-interactive`.
- [x] 4.3 Validate the implementation on the server via the admin ingestion path for `2508.18791`.

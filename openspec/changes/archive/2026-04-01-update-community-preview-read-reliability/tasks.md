## 1. Preview Rendering Hardening
- [x] 1.1 Expand LaTeX cleanup rules for optional citations, display math environments, control-command residue, and malformed inline remnants
- [x] 1.2 Normalize command-block behavior to avoid raw source leakage and replace non-readable snippets with reader-safe omitted notes
- [x] 1.3 Preserve math semantics by applying destructive cleanup only outside inline/display math segments
- [x] 1.4 Add regression tests covering `P.\\ lobata`, `\\PPNeSF`, `\\emph...\\penalty`, orphan `\\left/\\right`, mixed CJK macro residue, and center-tabular rendering

## 2. Preview Bridge Availability and Legacy Compatibility
- [x] 2.1 Add read-time sanitization for legacy preview payloads (legacy math class conversion and raw command-block stripping)
- [x] 2.2 Add fallback preview serving path when strict stale/untranslated heuristics reject regeneration but an existing readable preview asset is present
- [x] 2.3 Extend stale-preview detection patterns for leaked command blocks and TeX source tokens
- [x] 2.4 Add contract tests for fallback payload delivery and legacy preview cleanup

## 3. List/Detail State Consistency
- [x] 3.1 Introduce per-paper asset-map fetch path for list assembly
- [x] 3.2 Derive summary/latest asset and translated status using asset-type precedence instead of single newest timestamp
- [x] 3.3 Add regression test where `source_archive` is newer than `preview_html` yet list remains `completed`

## 4. Restart Cleanup Safety and Recovery
- [x] 4.1 Add startup purge toggle `ENABLE_STALE_PAPER_PURGE`
- [x] 4.2 Restrict non-success purge to non-public papers to prevent restart-driven deletion of public published content
- [x] 4.3 Keep interrupted-task failover and artifact cleanup semantics intact
- [x] 4.4 Add tests proving public papers are preserved while private/draft stale records are purged

## 5. DB Resilience and Frontend Rendering Fallback
- [x] 5.1 Expand `_run_db_blocking_with_retry` transient exception coverage and retry backoff behavior
- [x] 5.2 Add unit tests for timeout recovery and retry exhaustion behavior
- [x] 5.3 Add frontend fallback KaTeX rendering when preview enhancement pipeline fails or leaves math blocks unhydrated

## 6. Validation
- [ ] 6.1 Run `openspec validate update-community-preview-read-reliability --strict --no-interactive`

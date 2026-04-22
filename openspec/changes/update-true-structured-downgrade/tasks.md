## 1. Spec And Plan
- [x] 1.1 Add spec deltas for `latex-translation-core`, `hard-freeze`, and `translation-orchestration`
- [x] 1.2 Write the implementation plan under this change record
- [x] 1.3 Validate the OpenSpec change with strict mode

## 2. Tests
- [x] 2.1 Add unit coverage for relaxed section-level hard-freeze acceptance with stable high-risk anchors
- [x] 2.2 Add unit coverage that still rejects missing, duplicated, or reordered high-risk anchors
- [x] 2.3 Add unit coverage proving structured downgrade refuses source-English and fixed fallback boilerplate as successful target-language downgrade

## 3. Backend Implementation
- [x] 3.1 Implement risk-tiered hard-freeze verification in the LaTeX utils / translator boundary
- [x] 3.2 Thread the relaxed verification only through section-like prose paths without weakening strict env/list/math anchors
- [x] 3.3 Enforce target-language-only structured downgrade semantics in downgrade/orchestration code

## 4. Verification And Release
- [x] 4.1 Run focused backend tests and OpenSpec validation
- [x] 4.2 Inspect and stage the complete workspace state for this fix branch
- [x] 4.3 Commit all workspace contents on the fix branch, push, pull on the server, restart backend services, and verify health

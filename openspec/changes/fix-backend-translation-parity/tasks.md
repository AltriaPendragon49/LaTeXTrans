## 1. Spec and audit
- [x] 1.1 Add OpenSpec deltas for guard behavior, immutable chunks, and wrapper-preserving env translation
- [x] 1.2 Add backend regression audit script for paired backend/prototype outputs

## 2. Runtime fixes
- [x] 2.1 Relax structure guard blocking logic for macro-body false positives
- [x] 2.2 Add placeholder-aware chunk classification and immutable passthrough
- [x] 2.3 Preserve generic text environment wrappers during translation
- [x] 2.4 Short-circuit repeated repair on immutable/non-translatable chunks
- [x] 2.5 Protect synthetic placeholders during LLM transport for section and environment translation
- [x] 2.6 Fail closed to source content when section/list-environment env restoration leaves synthetic markers behind
- [x] 2.7 Mask residual raw structure tokens before payload invariants run
- [x] 2.8 Extract and reattach section structure shells around translatable core prose
- [x] 2.9 Split payload-invariant passthrough from generic API fallback / no-op retry
- [x] 2.10 Run post-compile target-language fallback even after successful compile when pending reports exist
- [x] 2.11 Add long-English-prose completeness validation for section outputs
- [x] 2.12 Preserve section wrappers or target-language body during section fallback reconstruction
- [x] 2.13 Accept starred section wrappers during reconstruction and fallback
- [x] 2.14 Preserve internal structure tokens inside fallback section bodies

## 3. Validation
- [x] 3.1 Add regression tests for structure guard
- [x] 3.2 Add regression tests for parser chunking and env translation
- [x] 3.3 Add regression tests for repair short-circuit behavior
- [x] 3.4 Validate OpenSpec and targeted backend tests
- [x] 3.5 Add regression coverage for synthetic placeholder transport masking and env-restore fallback
- [x] 3.6 Extend audit output with invariant passthrough, structure-shell, long-English, and pending-fallback metrics
- [x] 3.7 Preserve section wrappers or target-language body during section fallback reconstruction
- [x] 3.8 Audit final main tex for long English spans after reconstruction
- [x] 3.9 Add regression coverage for starred section reconstruction and internal section-body structure tokens

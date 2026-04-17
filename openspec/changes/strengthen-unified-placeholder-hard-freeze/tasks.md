## 1. Freeze Protocol
- [ ] 1.1 Define the full protected-token registry covering parser placeholders and internal payload sentinels.
- [ ] 1.2 Implement request-local opaque hard-freeze token generation with nonce/digest-backed uniqueness.
- [ ] 1.3 Implement strict token-stream verification and exact table-driven decode semantics.

## 2. Translator Integration
- [ ] 2.1 Route every structural-risk LLM entrypoint through the unified hard-freeze boundary.
- [ ] 2.2 Reject mutated placeholder responses without speculative boundary repair.
- [ ] 2.3 Preserve existing retry/fallback handling after hard-freeze protocol rejection.

## 3. Observability and Compatibility
- [ ] 3.1 Persist request-local hard-freeze audit metadata for replay/debugging.
- [ ] 3.2 Keep validator, repair, reconstruction, and compile fallback layers active as downstream defense in depth.
- [ ] 3.3 Add explicit error reasons/metrics for hard-freeze protocol violations.

## 4. Verification
- [ ] 4.1 Add tests for exact preservation, missing token, duplicate token, reordered token, and unknown token cases.
- [ ] 4.2 Add path coverage for sections, captions, generic text envs, list envs, and eqnarray envs.
- [ ] 4.3 Verify that rejected responses never decode into persisted placeholder-bearing translation state.

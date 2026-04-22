## 1. Spec And Design Record
- [x] 1.1 Record the canonical translated-PDF delivery contract and migration plan in OpenSpec.

## 2. Backend Regression Tests
- [x] 2.1 Add tests that prove translated asset persistence and backfill upgrade paths store trimmed canonical translated PDFs before public reads.
- [x] 2.2 Add tests that prove public translated preview resolution does not create a new trimmed delivery artifact at read time.
- [x] 2.3 Verify the new tests fail before implementation.

## 3. Backend Implementation
- [x] 3.1 Update translated asset recovery/persistence so canonical delivery PDFs are produced during asset creation and reusable backfill helpers.
- [x] 3.2 Update public translated preview/download resolution to reuse canonical assets without request-time trimming work.
- [x] 3.3 Keep source-PDF delivery behavior unchanged.

## 4. Existing Paper Migration
- [x] 4.1 Add a backfill script that upgrades existing translated PDF assets in place.
- [x] 4.2 Update backend file indexing for any new backend production file added by the backfill work.

## 5. Verification
- [x] 5.1 Run targeted backend tests for translated asset persistence and preview resolution.
- [x] 5.2 Run OpenSpec validation for the change.

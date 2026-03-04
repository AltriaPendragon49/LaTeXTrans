## ADDED Requirements
### Requirement: Stage 3 Sanitizer Execution Invariance
Stage 3 image sanitizer behavior implemented in the compiler MUST remain reachable through compile-failure image-error flow and MUST NOT be bypassed by orchestration refactors.

#### Scenario: Image-related compile failure still enters Stage 3
1. Given compilation failure logs include image-related signatures (for example `(pdf inclusion)` / `reading image failed`)
2. When fallback selection proceeds to Stage 3
3. Then the compiler MUST invoke the existing Stage 3 sanitizer entrypoint
4. And this change MUST NOT relocate sanitizer execution into external orchestration nodes.

#### Scenario: Multiline image-error variant triggers Stage 3
1. Given image-related log fragments are split across wrapped lines
2. When Stage 3 trigger detection runs
3. Then trigger detection MUST still enter Stage 3 sanitizer flow.

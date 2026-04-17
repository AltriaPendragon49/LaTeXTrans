## ADDED Requirements
### Requirement: Hard-Freeze Invariant Failures Short-Circuit Across Structural Subparts
The orchestration layer SHALL apply consistent passthrough handling for hard-freeze invariant failures across sections, captions, and environments without amplifying repeated retry work.

#### Scenario: Caption or environment invariant violation becomes explicit passthrough
1. Given a caption or environment translation attempt fails due to a hard-freeze or payload invariant violation
2. When orchestration handles the invalid attempt
3. Then the translated content MUST fall back to preserved source content for that subpart
4. And the subpart metadata MUST record an explicit passthrough status and stable fallback reason
5. And the pipeline MUST NOT route that same invalid attempt into deeper speculative recovery paths for that subpart.

#### Scenario: Repeated invariant failures do not duplicate failed-part tracking
1. Given the same section, caption, or environment identifier hits the same invalid-attempt path more than once in a run
2. When orchestration records failed-part tracking
3. Then the failed identifier MUST be stored only once per bucket
4. And downstream retry bookkeeping MUST NOT inflate work solely because the same invalid identifier was recorded repeatedly.

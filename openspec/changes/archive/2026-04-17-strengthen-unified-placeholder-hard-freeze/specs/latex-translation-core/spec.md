## MODIFIED Requirements
### Requirement: Placeholder Integrity and Recovery
The translation pipeline MUST aggressively protect and recover all injected placeholders and synthetic structural sentinels. For structural-risk LLM calls, this protection MUST happen through a unified hard-freeze transport protocol rather than relying on prompt compliance or fuzzy placeholder repair at the LLM boundary.

#### Scenario: Structural-risk payload uses opaque hard-freeze transport tokens
1. Given a section, caption, or environment payload that contains protected placeholders or sentinels
2. When the system prepares that payload for the LLM
3. Then the text sent to the LLM MUST contain opaque hard-freeze transport tokens instead of the original protected strings
4. And the transport tokens MUST remain the only acceptable protected-token representation in the raw model response.

#### Scenario: Exact transport-token preservation allows downstream decode
1. Given a model response whose hard-freeze token stream exactly matches the prepared request stream
2. When the boundary verifier accepts the response
3. Then the system MUST decode the transport tokens back to their original protected strings
4. And MUST continue through the existing validation and reconstruction pipeline.

#### Scenario: Boundary corruption does not enter fuzzy placeholder recovery
1. Given a model response whose hard-freeze token stream is missing, duplicated, reordered, or contains an unknown token
2. When the system evaluates the response
3. Then the system MUST reject the response before decoded translation state is updated
4. And MUST NOT invoke fuzzy placeholder recovery as a substitute for exact boundary verification.

## ADDED Requirements
### Requirement: Unified Hard-Freeze Coverage Across Structural-Risk Translation Paths
Every structural-risk LLM translation path MUST use the same hard-freeze preparation and verification contract.

#### Scenario: First-pass section translation uses unified hard-freeze
1. Given a normal section translation request
2. When the translator sends the request to the LLM
3. Then the request MUST pass through the unified hard-freeze boundary
4. And direct raw placeholder-bearing submission MUST NOT occur.

#### Scenario: Retranslation and environment recovery use unified hard-freeze
1. Given a retranslation, environment recovery, list rescue, or eqnarray row-safe translation request
2. When the translator sends the request to the LLM
3. Then the request MUST pass through the same unified hard-freeze boundary
4. And protocol rejection semantics MUST remain identical to first-pass translation.

### Requirement: Exact Token-Stream Equality for Accepted LLM Responses
Accepted LLM responses MUST preserve the exact request token stream for every hard-frozen protected artifact occurrence.

#### Scenario: Accepted output preserves occurrence order
1. Given a request with two occurrences of the same logical placeholder family
2. When the model response is accepted
3. Then the preserved hard-freeze token stream MUST match the original occurrence order exactly
4. And acceptance MUST NOT be based only on placeholder set equality or family-level equality.

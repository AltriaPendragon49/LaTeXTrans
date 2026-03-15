## MODIFIED Requirements
### Requirement: Removal of Structural Fallback
The translator agent MUST NOT execute speculative structural repair that injects LaTeX structure tokens, and structural validation failure MUST NOT imply immediate source-language rollback.

#### Scenario: Structural failure does not imply source rollback
1. Given a translation chunk fails structural validation
2. When the pipeline routes the chunk through C1/C2 handling
3. Then the system MUST preserve the target-language `trans_content` during validation
4. And it MUST only enter deterministic target-language downgrade handling after a failed compile attempt.

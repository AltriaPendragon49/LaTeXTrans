# ControlledRepairWorkflow Specification Deltas

## MODIFIED Requirements
### Requirement: Extremely Strict Controlled LLM Repair Prompting
Controlled LLM repair (Phase 2) execution MUST be attempted according to a strict global and per-segment budget (MAX_REPAIR_RETRIES, e.g., 3). The system MUST employ an extremely strict Prompt that explicitly forbids any form of translation or semantic rewriting, except under specific context-aware recovery conditions. The prompt MUST incorporate validation_evidence to target specific repairs (e.g., math balancing, placeholder preservation).

#### Scenario: Prompt constraints for structure repair
- **WHEN** an env triggers its Phase 2 repair execution
- **THEN** the LLM is prompted to fix structure exclusively using detailed validation_evidence
- **AND** the Prompt MUST explicitly prohibit translating the text or altering its semantics (unless handling total erasure)
- **AND** if the output still fails verifiable structure checks (e.g., math count mismatch, placeholder mismatch)
- **THEN** the system MUST increment the repair retry count and re-evaluate the budget rather than always moving to Phase 3 after the first attempt.
- **AND** if the budget is exhausted, it MUST move to Phase 3.

## ADDED Requirements
### Requirement: FallbackReport Emission and Routing
The system MUST emit a structured FallbackReport whenever a text segment is rolled back to the source language or subjected to an oversize downgrade. When a FallbackReport is present in the pipeline state, the orchestrator MUST route the segment to the targeted repair sub-graph instead of immediately proceeding to final PDF generation or source pass-through.

#### Scenario: Intercepting a Validated Error
- **Given** a translation chunk has failed structural validation
- **When** the ValidatorAgent emits a FallbackReport for this chunk
- **Then** the langgraph_orchestrator routes the chunk to the targeted repair nodes rather than triggering silent rollback.

### Requirement: TranslationRepairAgent Bounds and StructureRepairNode Determinism
The TranslationRepairAgent MUST operate under strict bounds: preserving placeholders, preserving protected tokens, and rejecting the introduction of any new macros. The StructureRepairNode MUST use deterministic, non-LLM logic to correct bracket and environment mismatches, rejecting repairs if safety constraints fail.

#### Scenario: Bracket Misalignment
- **Given** an AST diff shows an unclosed brace { in the target text
- **When** the StructureRepairNode processes the chunk
- **Then** it deterministically closes the brace if feasible, or rejects the repair if the closure scope is ambiguous.

### Requirement: Deterministic Ultimate Downgrade Renderer
If all targeted repair attempts fail or retry budgets are exhausted, the system MUST apply a deterministic ultimate downgrade renderer backfilled with target language text. The renderer MUST deterministically escape all LaTeX special characters ($ \ % # & { } _ ^ ~) and isolate the readable language into a minimal compilation-safe container. Code blocks and verbatim environments are explicitly excluded.

#### Scenario: Final safety net triggered
- **WHEN** all repair budgets are exhausted for a chunk
- **THEN** the system MUST execute the deterministic renderer
- **AND** the resulting string MUST be safe for TeX compilation regardless of original content errors.

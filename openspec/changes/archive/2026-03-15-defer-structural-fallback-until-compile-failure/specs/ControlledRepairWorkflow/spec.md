## MODIFIED Requirements
### Requirement: FallbackReport Emission and Routing
The system MUST emit a structured `FallbackReport` whenever a text segment is marked for structural fallback consideration or subjected to oversize downgrade. When a structural `FallbackReport` is present, the orchestrator MUST route it through repair and compile-aware fallback handling instead of immediately rolling the text back to the source language.

#### Scenario: Repair exhausted but compile not yet attempted
- **WHEN** all repair budget for a structural fallback candidate is exhausted
- **THEN** the system MUST perform the first PDF compilation attempt before any deterministic downgrade
- **AND** MUST NOT immediately render the unit with the deterministic downgrade renderer.

### Requirement: Deterministic Ultimate Downgrade Renderer
If the first compile attempt fails and structural fallback candidates remain, the system MUST apply a deterministic target-language downgrade renderer to those candidates, then perform at most one compile retry. The renderer input MUST be the last target-language text, not the source snapshot.

#### Scenario: Failed compilation triggers deterministic target-language downgrade
- **WHEN** the first compilation attempt fails
- **AND** one or more structural fallback candidates remain
- **THEN** the system MUST apply the deterministic downgrade renderer to the candidate units
- **AND** MUST pass the last target-language `trans_content` into the renderer
- **AND** MUST perform exactly one compile retry.

#### Scenario: Compile retry budget is exhausted
- **WHEN** deterministic target-language downgrade has already been applied once
- **AND** the subsequent compile retry still fails
- **THEN** the system MUST return `failed_compilation`
- **AND** MUST NOT start another downgrade or compile retry cycle.

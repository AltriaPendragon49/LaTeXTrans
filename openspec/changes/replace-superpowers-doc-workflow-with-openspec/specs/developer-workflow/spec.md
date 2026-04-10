## ADDED Requirements

### Requirement: OpenSpec Is The Sole Formal Workflow Record
For this repository, the formal record for approved changes, design decisions, execution plans, and migration notes SHALL live under `openspec/`, and active assistant workflow output MUST NOT create competing formal records under `docs/superpowers/`.

#### Scenario: Formalized design and planning records land in OpenSpec
- **WHEN** an assistant working in this repository formalizes a design, change proposal, task list, or supporting engineering record
- **THEN** that record SHALL be written under `openspec/changes/<change-id>/...`, `openspec/specs/<capability>/...`, or `openspec/changes/archive/...`
- **AND** it MUST NOT be created as an active formal artifact under `docs/superpowers/**`

#### Scenario: Repository no longer treats Superpowers docs as active workflow truth
- **WHEN** repository workflow instructions and active docs are reviewed
- **THEN** they SHALL identify OpenSpec as the formal documentation system of record
- **AND** they SHALL NOT describe `docs/superpowers/**` as an accepted destination for active design or planning output

### Requirement: Superpowers Skills Remain Available As Process Capability
The repository workflow SHALL preserve Superpowers skills as process aids for brainstorming, planning, verification, review, and routing, while redirecting their formalized outputs into OpenSpec-compatible records.

#### Scenario: Brainstorming remains available without creating a competing spec store
- **WHEN** the workflow invokes brainstorming for idea refinement or design approval
- **THEN** brainstorming SHALL still perform clarification, approach comparison, and approval gating
- **AND** the formalized result SHALL be captured in OpenSpec-compatible artifacts rather than `docs/superpowers/specs/**`

#### Scenario: Planning remains available without creating a competing plan store
- **WHEN** the workflow invokes planning after design approval
- **THEN** planning SHALL still decompose work into actionable execution tasks
- **AND** the formalized result SHALL be captured in OpenSpec-compatible artifacts rather than `docs/superpowers/plans/**`

### Requirement: Legacy Superpowers Documents Are Migrated Into OpenSpec
All active repository records currently stored under `docs/superpowers/` SHALL be migrated into appropriate OpenSpec locations before the competing directory is removed.

#### Scenario: Existing Superpowers docs are mapped and preserved
- **WHEN** the migration audits the current `docs/superpowers/` directory
- **THEN** every active file SHALL receive an explicit destination inside `openspec/`
- **AND** the migrated content SHALL exist in that destination before `docs/superpowers/` is removed

#### Scenario: Competing directory is removed after migration
- **WHEN** all active `docs/superpowers/` records have been migrated into OpenSpec
- **THEN** the repository SHALL remove the active `docs/superpowers/` directory
- **AND** active workflow output SHALL no longer recreate it

### Requirement: Workflow And Skill Audits Prevent Regression
The migration SHALL include repository and local-skill audits that prove the OpenSpec-only carrier rule and the preservation of Superpowers process capability.

#### Scenario: Repository audit confirms no active superpowers-doc outputs remain
- **WHEN** the repository is searched after migration
- **THEN** active workflow guidance SHALL show no remaining instructions to generate `docs/superpowers/**`
- **AND** any remaining references SHALL be limited to archived history or explicit migration evidence

#### Scenario: Skill-preservation review confirms capabilities remain intact
- **WHEN** the updated local and repository skill files are reviewed after migration
- **THEN** brainstorming, planning, verification, review, and workflow-routing skills SHALL still exist
- **AND** their documented process effects SHALL remain available even though their formal output carrier has changed to OpenSpec

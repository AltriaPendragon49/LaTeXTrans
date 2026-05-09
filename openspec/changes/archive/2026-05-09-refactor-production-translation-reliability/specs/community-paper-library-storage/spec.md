## ADDED Requirements
### Requirement: Community Publish Quality Gate
The community paper library SHALL publish canonical translated assets only after a production quality gate accepts the final task output and translation metadata.

#### Scenario: Quality gate runs before canonical asset sync
- **WHEN** a community paper task completes and prepares to sync `translated_pdf` or `preview_html` into the canonical community store
- **THEN** the system MUST run the community publish quality gate first
- **AND** assets MUST NOT become the latest public community assets unless the gate passes.

#### Scenario: Gate failure keeps artifacts for debugging
- **WHEN** the quality gate rejects a completed task
- **THEN** the system MUST preserve task artifacts for operator debugging
- **AND** it MUST NOT label the community paper as having a healthy new translated asset.

### Requirement: Fake Fallback Blocks Community Publish
The community publish quality gate MUST reject final outputs containing configured fake Chinese fallback phrases.

#### Scenario: Fake fallback phrase in preview
- **WHEN** generated preview HTML contains a configured fake fallback phrase
- **THEN** community publishing MUST fail with a machine-readable `fake_fallback_phrase` reason.

#### Scenario: Fake fallback phrase in PDF text
- **WHEN** extracted translated PDF text contains a configured fake fallback phrase
- **THEN** community publishing MUST fail with a machine-readable `fake_fallback_phrase` reason.

### Requirement: Source Fallback Is Tolerated Only When Small and Isolated
The community publish quality gate SHALL tolerate at most one short source fallback section under configurable thresholds and reject excessive or important source passthrough.

#### Scenario: One short source fallback is accepted
- **WHEN** final output contains exactly one source fallback section
- **AND** that section is below the configured absolute length threshold
- **AND** that section is below the configured percentage of natural-language body text
- **AND** it is not title, abstract, introduction, conclusion, or another configured high-importance section
- **THEN** the quality gate MAY accept the output.

#### Scenario: Multiple source fallback sections fail
- **WHEN** final output contains more than one source fallback section
- **THEN** community publishing MUST fail with a machine-readable `excessive_source_fallback` reason.

#### Scenario: Long source fallback fails
- **WHEN** final output contains a source fallback section exceeding configured length or body-ratio thresholds
- **THEN** community publishing MUST fail with a machine-readable `large_source_fallback` reason.

### Requirement: English Retention Gate Ignores Non-Prose Regions
The community publish quality gate SHALL evaluate English prose retention while ignoring non-prose regions that are expected to remain English or symbolic.

#### Scenario: Normal technical English is tolerated
- **WHEN** final output contains citations, bibliography entries, author names, affiliations, code/verbatim blocks, URLs, formulas, command names, dataset names, model names, acronyms, or technical terms
- **THEN** the quality gate MUST NOT count those regions as untranslated prose by default.

#### Scenario: High prose retention fails
- **WHEN** natural-language prose outside ignored regions exceeds configured English-retention thresholds
- **THEN** community publishing MUST fail with a machine-readable `high_source_language_retention` reason.

### Requirement: Provider Fatal States Block Community Publish
The community publish quality gate SHALL reject tasks that completed with fatal upstream provider states or exhausted provider failover.

#### Scenario: Fatal upstream state in task metadata
- **WHEN** task metadata records authentication failure, quota exhaustion, unsupported model, or exhausted provider failover
- **THEN** community publishing MUST fail with a machine-readable `fatal_provider_failure` reason
- **AND** the system MUST NOT treat any provider-failure fallback as valid translated content.

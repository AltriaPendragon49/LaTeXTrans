## MODIFIED Requirements
### Requirement: Paper guides are generated from title, abstract, and translated paper excerpts
The system SHALL generate paper-guide content from `title + abstract + hybrid module-relevant paper excerpts` rather than from only metadata or one shared full-paper payload.

#### Scenario: Curation prepares hybrid module analysis input
- **WHEN** the system starts paper-guide generation for a translated community paper
- **THEN** it SHALL include `title + abstract` in every module input as a shared semantic anchor
- **AND** it SHALL prefer module-relevant runtime artifacts that preserve both original-source text and translated excerpts from the paper body
- **AND** it MAY use preview-derived excerpts only as a bounded fallback when runtime artifacts are unavailable
- **AND** it SHALL not treat one shared full-paper payload as the normal source for all modules.

## ADDED Requirements
### Requirement: Five-module guide generation supports parallel first-pass execution
The system SHALL support concurrent first-pass generation of the five fixed guide modules so structured insight latency is not dominated by unnecessary serial execution.

#### Scenario: All guide modules start from the same prepared source batch
- **WHEN** the system has prepared source packets for `problem`, `solution`, `innovation`, `experiment`, and `future`
- **THEN** it MAY start those module generations concurrently
- **AND** each module SHALL keep its own backend-owned question and boundary prompt
- **AND** the system SHALL still persist the final modules in the stable fixed order.

### Requirement: Invalid guide modules are repaired incrementally after the parallel pass
The system SHALL repair only the guide modules that remain invalid after the parallel first pass instead of regenerating every module.

#### Scenario: One or more first-pass modules are unreadable or duplicated
- **WHEN** first-pass guide outputs contain empty, unreadable, or duplicated module content
- **THEN** the system SHALL retry only the affected modules
- **AND** it MAY use already-valid module briefs to reduce overlap during repair
- **AND** it SHALL keep already-valid module outputs unless a targeted repair explicitly replaces them.

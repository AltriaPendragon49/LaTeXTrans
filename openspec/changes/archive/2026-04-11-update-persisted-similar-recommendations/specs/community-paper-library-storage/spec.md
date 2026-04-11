## ADDED Requirements
### Requirement: Curated papers persist their final similar-recommendation package locally
The community paper library SHALL persist the final similar-paper recommendation package for newly curated public papers.

#### Scenario: Curation stores similar recommendations
- **WHEN** a newly curated paper completes recommendation generation during admin curation
- **THEN** the system SHALL store the final top-10 similar recommendation items locally under that paper
- **AND** each stored item SHALL preserve its display order, title, abstract, `arxiv_id`, `arxiv_url`, `community_paper_id`, and link type.

#### Scenario: Paper deletion removes persisted recommendations
- **WHEN** a community paper is hard-deleted
- **THEN** the system SHALL delete its persisted similar recommendation rows together with the rest of the paper-owned local records.

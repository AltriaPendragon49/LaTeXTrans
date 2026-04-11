## MODIFIED Requirements
### Requirement: Paper detail API exposes similar-paper recommendations for public community papers
The backend SHALL expose a public paper-detail recommendation API for similar papers under `/api/papers/{paper_id}/similar`.

#### Scenario: Newly curated papers read persisted recommendations
- **WHEN** a client requests similar papers for a public community paper that has persisted similar recommendations
- **THEN** the backend SHALL return the stored recommendation package directly
- **AND** it SHALL not re-run live candidate retrieval during that read.

#### Scenario: Persisted recommendations preserve ranking and routing metadata
- **WHEN** the backend returns persisted similar recommendations
- **THEN** the API SHALL preserve the stored display order and recommendation fields including `arxiv_id`, title, abstract, `arxiv_url`, `community_paper_id`, and `link_type`
- **AND** the client SHALL still be able to deep-link into the community detail page when `community_paper_id` exists.

#### Scenario: Legacy papers are not backfilled by this change
- **WHEN** a public community paper predates this persisted recommendation pipeline and has no stored similar recommendations
- **THEN** the backend SHALL not silently trigger a new live-retrieval generation path as part of this change
- **AND** it MAY return an empty or unavailable recommendation state for that paper.

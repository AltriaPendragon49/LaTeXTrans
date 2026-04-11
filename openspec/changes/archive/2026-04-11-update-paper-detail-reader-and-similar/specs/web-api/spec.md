## ADDED Requirements
### Requirement: Paper detail API exposes similar-paper recommendations for public community papers
The backend SHALL expose a public paper-detail recommendation API for similar papers under `/api/papers/{paper_id}/similar`.

#### Scenario: Similar recommendations rerank merged community and arXiv candidates
- **WHEN** a client requests similar papers for a public community paper
- **THEN** the backend SHALL retrieve normalized candidates from both the local public community library and arXiv official search/query results
- **AND** it SHALL rerank the merged candidate pool with a shared BM25-based scoring pass before returning the final results.

#### Scenario: Local BM25 recommendations exclude weak stopword-only or category-only collisions
- **WHEN** a local candidate only overlaps the current paper through stopwords or a bare category match without meaningful lexical overlap
- **THEN** the backend SHALL exclude that candidate from the local recommendation response
- **AND** it SHALL continue evaluating other local candidates before deciding whether to fall back to arXiv.

#### Scenario: Similar recommendations are ordered by score rather than source priority
- **WHEN** both community and arXiv candidates survive filtering in the merged candidate pool
- **THEN** the backend SHALL order the final recommendation list by reranked score
- **AND** it SHALL not force community items ahead of higher-scoring arXiv items solely because of their source.

#### Scenario: Similar recommendations return at most ten results from the reranked pool
- **WHEN** the merged candidate pool contains more than ten usable recommendation items
- **THEN** the backend SHALL return only the highest-scoring ten results
- **AND** it SHALL exclude the current paper from the returned results.

#### Scenario: Duplicate community and arXiv candidates are merged before final ranking
- **WHEN** the same paper is discovered through both the community library and the arXiv candidate set
- **THEN** the backend SHALL merge them into one recommendation item before final ranking
- **AND** it SHALL include the `community_paper_id` so the client can deep-link into the in-product detail page.

#### Scenario: Recommendation item matches an existing community paper
- **WHEN** a returned similar-paper candidate has an `arxiv_id` that already exists in the local public community library
- **THEN** the API SHALL include the matching local `community_paper_id`
- **AND** the client SHALL be able to route the user to the in-product paper detail page instead of only the external arXiv page.

#### Scenario: Recommendation item has no existing community match
- **WHEN** a returned similar-paper candidate does not exist in the local public community library
- **THEN** the API SHALL still return the candidate's `arxiv_id`, title, abstract, and official `arxiv_url`
- **AND** the response SHALL remain usable for an external arXiv jump.

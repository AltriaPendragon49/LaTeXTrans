## ADDED Requirements
### Requirement: Community paper list API supports paginated public feed reads
The public community paper list API MUST support paginated reads so clients can incrementally load the feed without requesting the entire corpus.

#### Scenario: Client requests the first latest-feed page
- **WHEN** a client calls `GET /api/papers` with `sort=latest`, `limit`, and `offset=0`
- **THEN** the API MUST return `items`, `total`, `offset`, `limit`, `has_more`, and `next_offset`
- **AND** the payload MUST contain only that page's items rather than the whole public list.

#### Scenario: First latest-feed page is cacheable
- **WHEN** the client requests the public latest feed with an empty query and `offset=0`
- **THEN** the backend MAY serve a short-lived cached first-page payload
- **AND** later public-paper mutations MUST invalidate that cache before the next response is generated.

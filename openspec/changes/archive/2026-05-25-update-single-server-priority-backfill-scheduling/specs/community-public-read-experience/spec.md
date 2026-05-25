## ADDED Requirements
### Requirement: Public feed thumbnails are warm-cache friendly
Public paper thumbnails MUST be available from cache whenever a previously warmed public paper appears on the homepage.

#### Scenario: Paper becomes publicly readable
- **WHEN** a paper transitions into a public readable state with source or translated PDF preview assets
- **THEN** the backend MUST schedule thumbnail cache warmup for the relevant public preview assets
- **AND** subsequent homepage thumbnail requests SHOULD reuse the cached rasterized image when it already exists.

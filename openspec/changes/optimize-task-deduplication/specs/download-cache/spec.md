# download-cache Specification

## ADDED Requirements

### Requirement: Download Cache Management

The system SHALL cache downloaded source files using a unique key based on source type, source ID, and version.

#### Scenario: Cache hit for previously downloaded paper

- **WHEN** user requests ArXiv paper "2401.12345" version "v1" that was previously downloaded
- **THEN** the cached path shall be returned immediately without network download

#### Scenario: Cache miss triggers new download

- **WHEN** user requests ArXiv paper "2401.99999" version "v1" that has never been downloaded
- **THEN** a new download shall be initiated and the result stored in cache upon completion

### Requirement: Concurrent Download Lock

The system SHALL prevent duplicate concurrent downloads of the same source file using a lock mechanism.

#### Scenario: Second request waits for ongoing download

- **WHEN** User B requests the same ArXiv paper that User A is currently downloading
- **THEN** User B's request shall wait for User A's download to complete and receive the cached path

#### Scenario: Lock released after download completes

- **WHEN** a download completes successfully
- **THEN** the lock shall be released and the cache entry shall be created

#### Scenario: Lock released on download failure

- **WHEN** a download fails
- **THEN** the lock shall be released, no cache entry shall be created, and the next request shall retry

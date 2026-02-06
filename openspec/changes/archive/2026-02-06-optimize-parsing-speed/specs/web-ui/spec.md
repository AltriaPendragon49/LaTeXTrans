## ADDED Requirements

### Requirement: Download Progress Updates
The frontend SHALL receive task status updates via Server-Sent Events (SSE) instead of polling during arXiv download operations.

The system MUST:
- Connect to `/api/task/{task_id}/stream` endpoint for real-time updates
- Automatically fall back to polling (2-second interval) if SSE connection fails
- Display granular progress stages: Downloading → Extracting → Parsing → Analyzing

#### Scenario: SSE connection for download progress
- **WHEN** user initiates arXiv download
- **THEN** the frontend SHALL establish SSE connection to receive progress updates
- **AND** display real-time progress without polling

#### Scenario: SSE connection failure fallback
- **WHEN** the SSE connection fails or times out
- **THEN** the system SHALL fall back to polling with 2-second interval
- **AND** log the fallback event for debugging

---

## ADDED Requirements

### Requirement: Reduced API Request Volume
The frontend MUST NOT generate more than 2 status queries per second during download operations.

#### Scenario: Request rate under normal SSE
- **WHEN** SSE connection is active
- **THEN** no polling requests SHALL be made
- **AND** API request rate SHALL be zero for status queries

#### Scenario: Request rate under fallback polling
- **WHEN** using fallback polling mode
- **THEN** polling interval SHALL be at least 2000ms
- **AND** API request rate SHALL NOT exceed 0.5 requests per second

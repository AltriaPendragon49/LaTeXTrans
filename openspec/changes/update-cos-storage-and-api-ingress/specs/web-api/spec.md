## ADDED Requirements
### Requirement: Community paper detail bootstrap payload remains lightweight
The web API SHALL keep community paper detail responses lightweight by returning reader bootstrap metadata and asset locators instead of embedding large reader bodies directly in the base detail response.

#### Scenario: Detail response for a preview-ready paper
- **WHEN** a client requests `GET /api/papers/{paper_id}` for a paper with translated preview assets
- **THEN** the API SHALL return metadata, reader state, and stable locators for preview/PDF assets
- **AND** it SHALL NOT require the base detail response to inline the full preview HTML body.

#### Scenario: Dedicated reader asset fetch remains available
- **WHEN** the client needs the actual preview HTML or PDF asset after loading paper detail bootstrap data
- **THEN** the API contract SHALL provide a dedicated asset-fetch path or signed asset locator
- **AND** the client SHALL not need to reconstruct asset paths from raw database fields.

### Requirement: Community asset APIs support object-storage delivery with local fallback
Community preview and download APIs SHALL support canonical assets that live either on object storage or on local disk.

#### Scenario: Object-storage-backed translated PDF is requested
- **WHEN** a client requests a translated community PDF whose canonical asset backend is object storage
- **THEN** the API SHALL resolve that asset through a supported delivery mode such as redirect, signed URL, or first-party proxy response
- **AND** the client-facing route contract SHALL remain stable.

#### Scenario: Local-disk-backed translated PDF is requested
- **WHEN** a client requests a translated community PDF whose canonical asset backend is local disk
- **THEN** the API SHALL continue serving that file through the existing local file response path
- **AND** local development SHALL remain functional without object storage.

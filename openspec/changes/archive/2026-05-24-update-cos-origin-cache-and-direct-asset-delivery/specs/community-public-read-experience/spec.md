## ADDED Requirements
### Requirement: Public PDF delivery balances stable iframe preview and COS direct downloads
The public reader SHALL use first-party Range-capable inline proxy responses for object-storage-backed PDF iframe previews, while explicit downloads SHALL continue to use signed COS redirects whenever available.

#### Scenario: Community translated PDF preview proxies COS with inline Range support
- **WHEN** a public community paper has an object-storage-backed translated PDF asset
- **THEN** `GET /api/papers/{paper_id}/translated-pdf` SHALL stream the signed COS object through the backend as an inline PDF response
- **AND** it SHALL forward browser `Range` requests upstream and preserve relevant `206 Partial Content`, `Accept-Ranges`, and `Content-Range` headers.

#### Scenario: Community source PDF preview proxies COS with inline Range support
- **WHEN** a public community paper resolves an object-storage-backed source PDF asset or raw-cache source PDF URL
- **THEN** `GET /api/papers/{paper_id}/source-pdf` SHALL stream the signed COS object through the backend as an inline PDF response
- **AND** it SHALL forward browser `Range` requests upstream and preserve relevant `206 Partial Content`, `Accept-Ranges`, and `Content-Range` headers.

#### Scenario: Ordinary task PDF preview proxies COS with inline Range support
- **WHEN** an ordinary completed translation task has an object-storage output manifest with a translated PDF
- **THEN** `GET /api/preview/{task_id}/pdf` SHALL stream the signed COS object through the backend as an inline PDF response
- **AND** it SHALL forward browser `Range` requests upstream and preserve relevant `206 Partial Content`, `Accept-Ranges`, and `Content-Range` headers
- **AND** local-disk deployments SHALL continue to serve the local PDF file as before.

#### Scenario: Explicit PDF downloads redirect to COS
- **WHEN** a public community paper or ordinary task has an object-storage-backed PDF available for explicit download
- **THEN** the download route SHALL redirect to a signed COS URL with attachment disposition when available
- **AND** the backend SHALL NOT proxy explicit download byte streams unless COS delivery is unavailable.

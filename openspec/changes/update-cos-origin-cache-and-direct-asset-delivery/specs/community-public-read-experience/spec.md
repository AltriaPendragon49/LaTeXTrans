## ADDED Requirements
### Requirement: Public PDF reads avoid backend byte proxying when COS direct delivery is available
The public reader SHALL use signed COS redirects for object-storage-backed source PDFs, translated PDFs, and ordinary task preview PDFs instead of streaming those PDF bytes through the backend.

#### Scenario: Community translated PDF preview redirects to COS
- **WHEN** a public community paper has an object-storage-backed translated PDF asset
- **THEN** `GET /api/papers/{paper_id}/translated-pdf` SHALL return a redirect to a signed COS URL suitable for inline PDF viewing
- **AND** the backend SHALL NOT proxy the PDF byte stream.

#### Scenario: Community source PDF preview redirects to COS
- **WHEN** a public community paper resolves an object-storage-backed source PDF asset or raw-cache source PDF URL
- **THEN** `GET /api/papers/{paper_id}/source-pdf` SHALL return a redirect to a signed COS URL suitable for inline PDF viewing
- **AND** the backend SHALL NOT proxy the PDF byte stream.

#### Scenario: Ordinary task preview redirects to COS
- **WHEN** an ordinary completed translation task has an object-storage output manifest with a translated PDF
- **THEN** `GET /api/preview/{task_id}/pdf` SHALL return a redirect to a signed COS URL suitable for inline PDF viewing
- **AND** local-disk deployments SHALL continue to serve the local PDF file as before.

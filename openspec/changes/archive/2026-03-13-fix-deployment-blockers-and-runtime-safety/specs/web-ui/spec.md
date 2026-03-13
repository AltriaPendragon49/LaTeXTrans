## ADDED Requirements
### Requirement: Required Frontend API Base Environment Variable
Frontend MUST require `VITE_API_BASE_URL` for all API calls.

#### Scenario: Shared resolver enforces API base env
- **WHEN** frontend initializes API client or API-consuming pages
- **THEN** API base URL MUST be loaded from a shared resolver bound to `VITE_API_BASE_URL`
- **AND** missing value MUST throw an explicit configuration error

### Requirement: Frontend Public Key Boundary
Frontend env MUST include only publishable Supabase keys.

#### Scenario: Frontend env excludes service-role key
- **WHEN** frontend `.env*` files are used
- **THEN** only public Supabase keys (URL + anon/publishable) MAY appear
- **AND** service-role key MUST NOT appear in any `VITE_*` variable

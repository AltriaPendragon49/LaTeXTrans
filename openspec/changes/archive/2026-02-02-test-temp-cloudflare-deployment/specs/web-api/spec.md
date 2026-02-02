# web-api Spec Delta

## MODIFIED Requirements

### Requirement: Extended CORS Configuration
The backend MUST allow cross-origin requests from Cloudflare Pages domains and local development origins.

#### Scenario: Request from Cloudflare Pages domain
- **GIVEN** the backend is configured with extended CORS settings
- **WHEN** a request comes from `https://*.pages.dev` origin
- **THEN** the request should be allowed with proper CORS headers
- **AND** credentials should be supported if required

#### Scenario: Request from local development
- **GIVEN** the backend is configured with extended CORS settings
- **WHEN** a request comes from `http://localhost:*` origin
- **THEN** the request should be allowed for development purposes

#### Scenario: Request from custom domain
- **GIVEN** the backend CORS settings include a custom domain pattern
- **WHEN** a request comes from the configured custom domain
- **THEN** the request should be allowed with proper CORS headers

## Related Capabilities
- [web-ui](../web-ui/spec.md) - Frontend requires CORS support for cross-origin API calls

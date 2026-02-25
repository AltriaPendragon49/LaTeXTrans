# web-ui Spec Delta

## MODIFIED Requirements

### Requirement: Environment-Based API Configuration
The frontend MUST support configurable API base URL through environment variables to enable deployment to different hosting environments.

#### Scenario: Frontend loads API URL from environment
- **GIVEN** the frontend is built with `VITE_API_URL` environment variable set
- **WHEN** the application initializes
- **THEN** API calls should be directed to the URL specified in `VITE_API_URL`
- **AND** if `VITE_API_URL` is not set, it should default to `http://localhost:8000/api`

#### Scenario: Development mode uses local backend
- **GIVEN** the frontend is running in development mode
- **WHEN** `.env.development` contains `VITE_API_URL=http://localhost:8000/api`
- **THEN** API calls should be directed to the local backend

#### Scenario: Production mode uses external backend
- **GIVEN** the frontend is built for production deployment
- **WHEN** `.env.production` contains a Cloudflare Tunnel URL
- **THEN** the built application should use the external backend URL

### Requirement: Static Asset Deployment
The frontend MUST be deployable to static hosting services (e.g., Cloudflare Pages) as a standalone SPA.

#### Scenario: Frontend deploys to Cloudflare Pages
- **GIVEN** the frontend is built with `npm run build`
- **WHEN** the `dist/` folder is deployed to Cloudflare Pages
- **THEN** all routes should correctly serve the SPA
- **AND** static assets should be properly cached

## Related Capabilities
- [web-api](../web-api/spec.md) - Backend CORS must allow Cloudflare Pages origins

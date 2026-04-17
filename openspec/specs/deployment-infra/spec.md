# deployment-infra Specification

## Purpose
TBD - created by archiving change add-persistent-deployment. Update Purpose after archive.
## Requirements
### Requirement: Fixed Backend Public URL
鍚庣 API SHALL 閫氳繃 Cloudflare Named Tunnel 鏆撮湶鍦ㄥ浐瀹氱殑鍏綉瀛愬煙鍚嶄笂锛屼笉鍥犻噸鍚€屽彉鍖栥€?

#### Scenario: Backend accessible via custom domain
- **WHEN** 澶栭儴璁惧璁块棶 `https://api.latextrans.online/api/health`
- **THEN** 杩斿洖鍋ュ悍妫€鏌?JSON 鍝嶅簲锛坰tatus=200锛?

#### Scenario: Tunnel restart preserves URL
- **WHEN** Named Tunnel 杩涚▼琚仠姝㈠苟閲嶆柊鍚姩
- **THEN** URL 涓嶅彉锛屾湇鍔′粛鍙甯歌闂?

### Requirement: Frontend Custom Domain

前端 SHALL 通过自定义域名提供访问，支持 HTTPS。

#### Scenario: Frontend accessible via custom domain

- **WHEN** 用户在手机浏览器访问 `https://latextrans.online`
- **THEN** 页面正常加载，显示 LaTeXTrans 界面

### Requirement: Dynamic API URL Resolution
Frontend API calls SHALL use environment variable `VITE_API_BASE_URL` and MUST NOT hardcode localhost fallback.

#### Scenario: Production build has no hardcoded localhost fallback
- **WHEN** frontend is built in production mode
- **THEN** build artifacts MUST NOT contain `localhost:8000`

#### Scenario: Missing API base env fails fast
- **WHEN** `VITE_API_BASE_URL` is not set
- **THEN** frontend MUST throw an explicit configuration error
- **AND** frontend MUST block API request creation

#### Scenario: API requests append /api namespace
- **WHEN** frontend composes backend request URLs
- **THEN** request paths SHALL be formed as `${VITE_API_BASE_URL}/api/...`
- **AND** callers MUST NOT bypass this contract with non-prefixed paths such as `/history`.

### Requirement: Auth Redirect Configuration

认证邮件和重定向 SHALL 指向生产环境域名。

#### Scenario: Email confirmation redirects to production domain

- **WHEN** 用户在手机上点击确认邮件中的链接
- **THEN** 浏览器跳转到 `https://latextrans.online` 并完成账户激活

### Requirement: Simplified Deployment Script

部署脚本 SHALL 支持一键部署，代码更新后可快速重新部署。

#### Scenario: Frontend redeployment after code change

- **WHEN** 开发者修改了前端代码并执行部署脚本
- **THEN** 前端自动构建并部署到 Cloudflare Pages，无需手动输入 Tunnel URL

#### Scenario: Backend restart without URL change

- **WHEN** 开发者修改了后端代码并重启 FastAPI 服务
- **THEN** `api.latextrans.online` 自动恢复连接，前端无需任何操作

### Requirement: Runtime-Only Container Contract
The runtime image MUST NOT be used without host code mount and runtime env injection, and the injected backend runtime configuration MUST include the business database connection required by local auth and community persistence.

#### Scenario: Required backend mount and env injection
- **WHEN** backend container starts
- **THEN** `/app/backend` MUST be mounted from host
- **AND** backend `.env` MUST be injected
- **AND** `backend/data/*` MUST be writable

#### Scenario: Business database wiring is present at runtime
- **WHEN** backend container starts with local auth and community persistence enabled
- **THEN** runtime env injection MUST provide a resolvable business database URL such as `DATABASE_URL`
- **AND** startup reconciliation, local auth session persistence, and community-paper persistence MUST be able to open that database without manual in-container edits
- **AND** missing database wiring MUST be treated as a deployment contract violation rather than an acceptable steady-state configuration

#### Scenario: Forbidden naked runtime image run
- **WHEN** runtime image is launched without mounting `/app/backend`
- **THEN** deployment documentation MUST mark this pattern as forbidden

### Requirement: Loopback-Only Host Publishing
Backend service exposure on shared host MUST be loopback-only.

#### Scenario: Host loopback port publish
- **WHEN** backend container is launched in production
- **THEN** host publish MUST be `127.0.0.1:9001:9001`
- **AND** Nginx MUST proxy to `http://127.0.0.1:9001`

### Requirement: Production Worker Guardrail
Production runtime SHALL default to a single worker until runtime-state is fully externalized.

#### Scenario: Runtime command uses one worker
- **WHEN** runtime starts with default command
- **THEN** `uvicorn` worker count MUST be `1`

### Requirement: Backend Secret Boundary and Rotation
Backend-only credentials MUST remain server-only, and exposed secrets MUST be rotated.

#### Scenario: Frontend env excludes service-role key
- **WHEN** frontend env files are prepared
- **THEN** frontend env MUST NOT contain backend-only service-role, database, or admin secrets

#### Scenario: Exposure remediation documented
- **WHEN** deployment documentation is reviewed
- **THEN** it MUST include a mandatory secret-rotation notice for any previously exposed backend-only credentials

### Requirement: Cloudflare-managed API ingress shields the production origin
Production browser traffic SHALL reach `api.latextrans.online` through a Cloudflare-managed edge path rather than depending on direct public browser access to the CVM origin TLS endpoint.

#### Scenario: External browser reaches the API through the Cloudflare edge
- **WHEN** an external browser requests `https://api.latextrans.online/api/health`
- **THEN** the request SHALL be served through the Cloudflare-managed ingress path
- **AND** the response SHALL remain stable for normal browser TLS and HTTP behavior without direct public origin dependence.

#### Scenario: Production origin is not the browser-facing durability boundary
- **WHEN** production API ingress is configured
- **THEN** the CVM origin SHALL act as an internal or Cloudflare-facing origin rather than the primary direct browser TLS endpoint
- **AND** deployment validation SHALL confirm the public route does not rely on direct origin exposure for steady-state browser access.

### Requirement: Production runtime artifact persistence is object-storage-backed with ephemeral origin cache
Production runtime artifacts SHALL use object storage as the canonical durable store, while local origin disk acts only as a temporary cache.

#### Scenario: Production task artifact is persisted successfully
- **WHEN** production generates a retained upload, output, preview, PDF, or task-log artifact
- **THEN** the system SHALL upload the canonical copy to object storage
- **AND** it SHALL remove the local cached copy after that artifact is no longer needed by the active task stage.

#### Scenario: Local development runs without object storage
- **WHEN** object storage is not configured in a local development environment
- **THEN** the backend SHALL continue using the existing local-disk storage layout
- **AND** developers SHALL not be required to provision COS for normal local iteration.


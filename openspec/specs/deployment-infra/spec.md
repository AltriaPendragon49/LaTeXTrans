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

### Requirement: Production COS deployments keep local asset residue bounded
Production COS deployments SHALL have an operator-verified cleanup/audit path so local runtime cache residue does not grow into durable-asset storage again.

#### Scenario: Cleanup audit runs after COS deployment
- **WHEN** production runs with `STORAGE_BACKEND_MODE=cos`
- **THEN** operators SHALL be able to run a cleanup audit that reports local residue under COS-managed upload, output, community paper, failed-task, and temp storage roots
- **AND** the audit SHALL include counts, sizes, ages, skipped paths, and errors.

#### Scenario: Destructive cleanup follows verification
- **WHEN** a cleanup execute run is enabled in production
- **THEN** it SHALL use the same guarded candidate rules as dry-run
- **AND** production verification SHALL confirm public asset routes still work after cleanup.

### Requirement: Production COS Asset Cutover
Production operations SHALL provide a guarded migration path that converts local-disk production assets to COS-backed durable storage without losing current public asset delivery.

#### Scenario: Dry-run manifest precedes destructive operations
- **WHEN** an operator prepares the production asset migration
- **THEN** the system SHALL produce a dry-run manifest listing COS orphan deletion candidates, local files to upload, database rows to update, same-key conflicts, and local cleanup candidates
- **AND** the operator SHALL be able to review this manifest before COS deletion, database updates, or local cleanup execute.

#### Scenario: Writes are paused during cutover
- **WHEN** production asset storage is being cut over from local disk to COS
- **THEN** production write paths SHALL be paused or placed into a maintenance window
- **AND** the migration SHALL not run while new translation outputs or community paper assets can be written to local disk.

#### Scenario: COS mode is verified before local cleanup
- **WHEN** local assets have been uploaded and database pointers have been switched to COS
- **THEN** backend and public API health checks SHALL pass in COS mode
- **AND** representative preview and download routes SHALL resolve assets from COS before migrated local asset directories are deleted.

#### Scenario: Final state reports storage authority
- **WHEN** the migration is complete
- **THEN** the operator report SHALL include final disk usage, COS object totals, MySQL storage-backend counts, and public health-check evidence.

### Requirement: Shared Redis service backs public community-paper discovery state
Production deployment SHALL provide a shared Redis service for public community-paper feed cache and ranking state.

#### Scenario: Multiple backend instances serve one public feed state
- **WHEN** multiple backend processes or hosts serve public `GET /api/papers` requests
- **THEN** they SHALL read and write the same Redis-backed public feed cache and ranking indexes
- **AND** steady-state correctness SHALL NOT depend on process-local public feed memory.

#### Scenario: Redis outage falls back to canonical reads
- **WHEN** the shared Redis service is unavailable or unhealthy
- **THEN** the backend SHALL fall back to the canonical database-backed public read path
- **AND** it SHALL NOT reintroduce divergent process-local feed caches as the production durability mechanism.

### Requirement: Public feed index maintenance is singleton-safe
Any scheduled rebuild, repair, or backfill path for Redis-backed public community-paper indexes SHALL run under singleton-safe execution.

#### Scenario: Scheduled index maintenance runs in production
- **WHEN** the system rebuilds or repairs the Redis-backed `latest`, `views`, or `likes` indexes
- **THEN** that work SHALL run in a dedicated worker role or under a distributed singleton lock
- **AND** multiple web instances SHALL NOT race to rebuild the same public index set concurrently.

#### Scenario: Scheduled rebuild swaps indexes atomically
- **WHEN** the system performs a full scheduled rebuild of a Redis-backed public feed index
- **THEN** it SHALL populate a temporary Redis key first
- **AND** it SHALL atomically promote the completed temporary key into the live index key rather than exposing a delete-then-rebuild gap to readers.

### Requirement: Single-server web and worker runtimes can be split safely
The deployment MUST support running the user-facing backend and the admin backfill executor as separate runtime roles on the same host.

#### Scenario: Web runtime serves traffic without owning admin backfill loops
- **WHEN** the backend process is started with runtime role `web`
- **THEN** it MUST initialize user-facing HTTP handling
- **AND** it MUST NOT start admin curation polling, admin delete polling, or orphan cleanup loops that belong to the background executor.

#### Scenario: Worker runtime owns background admin polling
- **WHEN** the backend process is started with runtime role `worker`
- **THEN** it MUST poll queued admin curation and delete jobs from durable storage
- **AND** it MAY skip legacy global restart reconciliation that is unsafe while translation ownership is split across runtimes.


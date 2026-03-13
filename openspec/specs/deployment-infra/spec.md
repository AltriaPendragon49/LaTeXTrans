# deployment-infra Specification

## Purpose
TBD - created by archiving change add-persistent-deployment. Update Purpose after archive.
## Requirements
### Requirement: Fixed Backend Public URL

后端 API SHALL 通过 Cloudflare Named Tunnel 暴露在固定的公网子域名上，不因重启而变化。

#### Scenario: Backend accessible via custom domain

- **WHEN** 外部设备访问 `https://api.latextrans.online/health`
- **THEN** 返回健康检查 JSON 响应（status=200）

#### Scenario: Tunnel restart preserves URL

- **WHEN** Named Tunnel 进程被停止并重新启动
- **THEN** URL 不变，服务仍可正常访问

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

### Requirement: Supabase Auth Redirect Configuration

Supabase Auth 确认邮件和重定向 SHALL 指向生产环境域名。

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
The runtime image MUST NOT be used without host code mount and runtime env injection.

#### Scenario: Required backend mount and env injection
- **WHEN** backend container starts
- **THEN** `/app/backend` MUST be mounted from host
- **AND** backend `.env` MUST be injected
- **AND** `backend/data/*` MUST be writable

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

### Requirement: Service Role Secret Boundary and Rotation
Service-role credentials MUST remain backend-only, and exposed keys MUST be rotated.

#### Scenario: Frontend env excludes service-role key
- **WHEN** frontend env files are prepared
- **THEN** `VITE_SUPABASE_SERVICE_ROLE_KEY` MUST NOT be present

#### Scenario: Exposure remediation documented
- **WHEN** deployment documentation is reviewed
- **THEN** it MUST include a mandatory key-rotation notice for exposed service-role credentials


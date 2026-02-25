## ADDED Requirements

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

前端所有 API 调用 SHALL 统一使用环境变量 `VITE_API_URL`，不硬编码 localhost。

#### Scenario: No hardcoded localhost in production build

- **WHEN** 前端以 production 模式构建
- **THEN** 构建产物中不包含 `localhost:8000` 字符串

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

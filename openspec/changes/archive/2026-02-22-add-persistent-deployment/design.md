# 持久化部署架构设计

## 当前架构

```
用户浏览器 --> latextrans.pages.dev (Cloudflare Pages)
                  |
                  | VITE_API_URL (硬编码临时 Tunnel URL)
                  v
              cloudflared tunnel --url http://localhost:8000
                  |
                  v
              本地 FastAPI (localhost:8000)
```

**问题**：
- `cloudflared tunnel --url` 是快速隧道（Quick Tunnel），每次重启生成随机 URL
- 前端必须在每次 Tunnel URL 变化时重新构建和部署
- Supabase Auth 确认邮件中的 redirect URL 指向 `localhost:5173`

## 目标架构

```
                     latextrans.online (Spaceship DNS → Cloudflare NS)
                           |
          +----------------+----------------+
          |                                 |
   app.latextrans.online              api.latextrans.online
   (Cloudflare Pages)                 (Cloudflare Named Tunnel)
          |                                 |
          v                                 v
     React 前端 (静态)               本地 FastAPI (:8000)
```

## 方案选择与分析

### 方案一：Cloudflare Named Tunnel + 自定义域名 ✅ 推荐

**前端部署**：
- Cloudflare Pages 已在使用（`latextrans.pages.dev`）
- 添加自定义域名 `app.latextrans.online`（或直接 `latextrans.online`）→ Cloudflare Pages 自动配置 DNS + SSL

**后端部署**：
- 将临时 Tunnel 升级为 **Named Tunnel**（命名隧道）
- 命名隧道 + `cloudflared` 配置文件 = 固定 URL
- 绑定子域名 `api.latextrans.online` 到命名隧道
- 每次重启只需 `cloudflared tunnel run <tunnel-name>`，URL 不变

**优点**：
- 零额外成本（Cloudflare Tunnel 免费）
- 后端继续在本地运行，无需云服务器
- URL 永久固定，不需要重新部署前端
- 自动 HTTPS（Cloudflare 管理证书）

**缺点**：
- 后端仍依赖本地电脑运行（电脑关机 = 服务不可用）
- 需要保持 `cloudflared` 进程运行

### 方案二：云服务器部署后端（未来可选）

将后端部署到 VPS/云服务器（如 AWS EC2、阿里云等），实现 24/7 可用。

**不在本次提案范围内**，因为：
- 需要额外成本
- 需要 Docker 化部署（LaTeX 编译环境）
- 当前阶段主要目标是解决"手机无法访问"的问题

## DNS 迁移步骤

将 Spaceship 域名的 DNS 管理迁移到 Cloudflare：

1. 在 Cloudflare 添加站点 `latextrans.online`（Free 计划）
2. Cloudflare 提供两个 NS 记录
3. 在 Spaceship 域名管理中，将 Nameservers 修改为 Cloudflare 的 NS
4. 等待 DNS 传播（通常 10min~24h）
5. Cloudflare 确认站点激活

> **注意**：迁移 DNS 到 Cloudflare 不影响已有的 Spacemail 邮箱服务。Cloudflare 会自动导入现有 DNS 记录（包括 MX 记录），但迁移前应确认 MX 记录已正确导入。

## 后端 Named Tunnel 配置

```yaml
# ~/.cloudflared/config.yml
tunnel: <TUNNEL_UUID>
credentials-file: ~/.cloudflared/<TUNNEL_UUID>.json

ingress:
  - hostname: api.latextrans.online
    service: http://localhost:8000
  - service: http_status:404
```

创建步骤：
```bash
# 1. 登录 Cloudflare
cloudflared tunnel login

# 2. 创建命名隧道
cloudflared tunnel create latextrans-api

# 3. 配置 DNS CNAME（自动）
cloudflared tunnel route dns latextrans-api api.latextrans.online

# 4. 运行隧道
cloudflared tunnel run latextrans-api
```

## 前端自定义域名

在 Cloudflare Pages Dashboard 中：
1. 进入 `latextrans` 项目 → Custom domains
2. 添加 `latextrans.online`（或 `app.latextrans.online`）
3. Cloudflare 自动配置 DNS 和 SSL 证书

## Supabase Auth 配置更新

在 Supabase Dashboard → Authentication → URL Configuration 中：
- **Site URL**: `https://latextrans.online`（或 `https://app.latextrans.online`）
- **Redirect URLs**: 添加 `https://latextrans.online/**` 和 `https://app.latextrans.online/**`

## 代码更新时的部署流程

代码更新后，重新部署非常简单：

### 前端代码更新
```bash
# 只需重新执行部署脚本（不再需要传 Tunnel URL）
cd frontend
npm run build
wrangler pages deploy dist --project-name latextrans
```

### 后端代码更新
```bash
# 后端是本地运行的，只需重启服务即可
# 停止当前服务 (Ctrl+C)
# 重新启动
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
# Tunnel 保持运行即可，不需要重新配置
```

## 需要用户确认的问题

1. **域名选择**：前端用 `latextrans.online` 还是 `app.latextrans.online`？
   - 建议直接用 `latextrans.online`（更简洁）
2. **后端子域名**：`api.latextrans.online` 是否满足需求？
3. **DNS 迁移**：是否同意将 Spaceship 的 DNS Nameservers 切换到 Cloudflare？
   - 这是使用 Cloudflare Tunnel 自定义域名的前提
   - 邮箱（Spacemail）仍可正常使用，只要 MX 记录保留

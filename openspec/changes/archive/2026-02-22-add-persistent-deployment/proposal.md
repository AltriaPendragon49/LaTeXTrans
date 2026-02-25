# Change: Add Persistent Deployment via Custom Domain + Cloudflare

## Why

当前部署方案是临时性的——后端通过 `cloudflared tunnel --url` 生成随机 URL（每次重启变化），导致手机/其他设备无法确认 Supabase 注册邮件（链接指向 localhost:5173），且每次重启需重新部署前端。用户已购买域名 `latextrans.online`，需要持久化部署以解决多设备访问问题。

## What Changes

- 将 Spaceship 域名的 DNS Nameservers 迁移到 Cloudflare
- 通过 Cloudflare Named Tunnel 为后端创建固定公网 URL（`api.latextrans.online`）
- 为 Cloudflare Pages 前端绑定自定义域名（`latextrans.online`）
- 修复前端代码中硬编码的 `localhost:8000` URL（`Comparisons.tsx`、`Processing.tsx`、`TerminologyTable.tsx`）
- 更新 Supabase Auth 的 Site URL 和 Redirect URLs
- 在 signUp 中添加 `emailRedirectTo` 参数
- 更新 CORS 配置和部署脚本
- 更新 `start.md` 文档

## Impact

- Affected specs: `deployment-infra`（新增）、`web-ui`、`user-auth`
- Affected code: `frontend/src/pages/Comparisons.tsx`、`frontend/src/pages/Processing.tsx`、`frontend/src/components/TerminologyTable.tsx`、`frontend/src/contexts/AuthContext.tsx`、`frontend/.env.production`、`backend/app/core/config.py`、`scripts/start-tunnel.ps1`、`scripts/deploy-frontend.ps1`、`start.md`

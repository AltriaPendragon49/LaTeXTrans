# Tasks — add-persistent-deployment

## 阶段一：基础设施配置（手动操作）

- [ ] 1. 在 Cloudflare 添加站点 `latextrans.online`（Free 计划），获取 Cloudflare NS 地址
- [ ] 2. 在 Spaceship 域名管理中将 Nameservers 切换为 Cloudflare NS
- [ ] 3. 等待 DNS 传播并确认 Cloudflare 站点激活
- [ ] 4. 在 Cloudflare 确认邮箱相关 MX 记录已正确导入（保证 Spacemail 正常工作）

## 阶段二：后端 Named Tunnel 配置（手动 + 脚本）

- [ ] 5. 运行 `cloudflared tunnel login` 登录 Cloudflare 账户
- [ ] 6. 运行 `cloudflared tunnel create latextrans-api` 创建命名隧道
- [ ] 7. 创建 `~/.cloudflared/config.yml` 配置文件
- [ ] 8. 运行 `cloudflared tunnel route dns latextrans-api api.latextrans.online` 自动创建 DNS CNAME
- [ ] 9. 测试 `cloudflared tunnel run latextrans-api` 并验证 `https://api.latextrans.online/health` 可访问
- [ ] 10. 更新 `scripts/start-tunnel.ps1` 使用命名隧道替代快速隧道

## 阶段三：前端配置与代码修复

- [ ] 11. 修复前端硬编码 `localhost:8000` URL（`Comparisons.tsx`、`Processing.tsx`、`TerminologyTable.tsx`）
- [ ] 12. 更新 `.env.production` 设置 `VITE_API_URL=https://api.latextrans.online/api`
- [ ] 13. 在 Cloudflare Pages Dashboard 添加自定义域名 `latextrans.online`
- [ ] 14. 更新 `scripts/deploy-frontend.ps1` 脚本（移除 TunnelUrl 参数依赖）
- [ ] 15. 更新 CORS 配置添加 `https://latextrans.online`

## 阶段四：Supabase Auth 配置

- [ ] 16. 在 Supabase Dashboard 更新 Site URL 为 `https://latextrans.online`
- [ ] 17. 在 Supabase Dashboard 添加 Redirect URLs: `https://latextrans.online/**`
- [ ] 18. 在前端 `signUp` 方法中添加 `emailRedirectTo` 参数

## 阶段五：部署与验证

- [ ] 19. 重新构建并部署前端到 Cloudflare Pages
- [ ] 20. 在手机上访问 `https://latextrans.online` 验证页面可访问
- [ ] 21. 在手机上注册新用户，验证确认邮件链接指向正确域名
- [ ] 22. 更新 `start.md` 文档反映新的部署流程

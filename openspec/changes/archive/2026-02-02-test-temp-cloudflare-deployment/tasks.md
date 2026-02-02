# Tasks for add-cloudflare-deployment

## Phase 1: 前端配置

- [x] 1.1 修改 `frontend/src/lib/api.ts` 支持环境变量
- [x] 1.2 创建 `frontend/.env.example` 环境变量模板
- [x] 1.3 创建 `frontend/.env.development` 本地开发配置

## Phase 2: 后端配置

- [x] 2.1 更新 `backend/app/core/config.py` CORS 配置，支持 Cloudflare 域名

## Phase 3: 部署配置

- [x] 3.1 创建 `frontend/wrangler.toml` Cloudflare Pages 配置
- [x] 3.2 创建 `scripts/start-tunnel.ps1` Tunnel 启动脚本
- [x] 3.3 创建 `scripts/deploy-frontend.ps1` 前端部署脚本
- [x] 3.4 更新 `README.md` 添加部署说明

## Phase 4: 验证

- [x] 4.1 本地验证：确认环境变量正确加载 ✓ 前端构建成功
- [ ] 4.2 Tunnel 验证：确认后端可通过公网访问 (需要用户执行)
- [ ] 4.3 端到端验证：外部用户完成完整翻译流程 (需要用户执行)

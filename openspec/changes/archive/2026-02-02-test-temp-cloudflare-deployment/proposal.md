# test-temp-cloudflare-deployment

部署前端到 Cloudflare Pages，并通过 Cloudflare Tunnel 暴露本地后端，实现零成本的外部访问能力。

## Context

用户希望让朋友体验 LaTeXTrans 系统，需要：
1. 将前端部署到公网（选择 Cloudflare Pages，免费）
2. 后端保持本地运行（通过 Cloudflare Tunnel 暴露）

## Scope

- **IN SCOPE:**
  - 前端环境变量配置（支持动态 API 地址）
  - Cloudflare Pages 部署配置
  - 后端 CORS 配置更新
  - 部署文档和启动脚本

- **OUT OF SCOPE:**
  - 后端代码逻辑修改
  - 数据库或持久化存储
  - 用户认证（当前为临时用户模式）

## Success Criteria

1. 前端成功部署到 Cloudflare Pages
2. 外部用户可通过公网 URL 访问前端
3. 前端可通过 Cloudflare Tunnel 调用本地后端 API
4. 完整翻译流程可在外部网络环境下正常工作

## 相关能力

| Capability | Impact |
|------------|--------|
| web-ui | MODIFIED - 添加环境变量配置 |
| web-api | MODIFIED - 更新 CORS 配置 |

## References

- [Cloudflare Pages 文档](https://developers.cloudflare.com/pages/)
- [Cloudflare Tunnel 文档](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/)

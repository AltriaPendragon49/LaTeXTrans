# Tasks: API 修复与同步

- [x] **基础设施更新**
  - [x] 更新 `.env` 中的 `LLM_API_KEY` 为英伟达新密钥
  - [x] 移除代码中及启动脚本中的硬编码回退逻辑，强制依赖环境变量

- [x] **后端 URL 处理修复**
  - [x] 在 `translate.py` 中实现 `normalize_base_url` 助手函数
  - [x] 更新 `build_llm_config` 及相关端点使用归一化逻辑
  - [x] 验证对 Nvidia `v1/chat/completions` 完整路径的兼容性

- [x] **模型一致性同步**
  - [x] 在 `run_translation` 中增加模型同步逻辑，将真实模型名写回 `advanced_config`
  - [x] 调用 `task_manager.update_task` 持久化真实模型信息
  - [x] 更新前端 `useStore.ts` 中的 fallback 模型，由 `gpt-4.1-mini` 改为 `qwen/qwen3-235b-a22b`

- [x] **前端 UI/UX 深度优化**
  - [x] 优化 ArXiv 下载等待 Tip 文案，并调整为交互式可收起状态
  - [x] 在高级配置栏增加 Nvidia 免费 API 的性能与质量风险预警
  - [x] 实现基于 React 状态的全站提示框“点击即消失”逻辑及平滑动画设计

- [x] **验证与文档化**
  - [x] 手动测试 Nvidia API 调用流程，确认不再出现 403/404
  - [x] 验证前端 Dashboard 提示框的隐藏交互与动画流畅度
  - [x] 检查 SUPABASE 数据库/翻译历史，验证 `translation_model` 字段记录准确
  - [x] 完成 OpenSpec 归档文档的同步更新

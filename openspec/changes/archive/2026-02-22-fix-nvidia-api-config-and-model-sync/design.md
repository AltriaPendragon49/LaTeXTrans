# Design: API 归一化与模型同步机制

## API URL 归一化 (Normalization)
为了兼容多样化的 LLM 提供商，后端引入了 `normalize_base_url` 助手函数。

### 处理逻辑
1. **防重复追加**：如果 URL 已包含 `/chat/completions`，则认为已经是完整路径，直接返回。
2. **自动补全**：对于仅提供域名的 API 路径，自动追加 `/v1/chat/completions`。
3. **域名剔除逻辑 (已取消)**：曾尝试对 `nvidia.com` 进行特殊截断，但由于系统直接使用 `POST` 请求 `base_url`，所有 API 均需完整路径，因此取消特殊映射，统一采用补全策略。

## 翻译模型同步 (Model Sync)
由于系统支持“使用作者 API”和“自定义 API”，前端传入的 `translation_model` 字段往往是默认占位符。

### 同步流程
1. **任务初始化**：接收前端请求，创建初步任务记录。
2. **配置构建**：调用 `build_llm_config()`，根据 `use_author_api` 开关决定最终使用的密钥、URL 和模型名。
3. **回写数据库**：
   - 获取 `llm_config` 中的真实模型名。
   - 若与 `advanced_config` 中的记录不符，强制更新 `advanced_config.translation_model`。
   - 调用 `task_manager.update_task` 将最新配置同步至 Supabase。
4. **终端一致性**：后续 `translator_agent` 将直接使用更新后的数据库记录进行显示。

## 安全性增强
- **环境变量隔离**：敏感密钥严格限制在 `backend/.env` 中。
- **移除回退逻辑**：在 `translate.py` 和启动脚本中，移除所有针对默认密钥的“代码级默认值”，确保在未正确配置环境变量时产生明确报错而非回退到无效密钥。
26: 
27: ## 用户界面优化 (User Interface Refinements)
28: 
29: 为了提升用户在等待 arXiv 下载及配置 API 时的体验，前端 Dashboard 引入了交互式引导机制。
30: 
31: ### 交互式提示状态 (Dismissible State)
32: 1. **状态驱动展示**：使用 React 的 `useState` (`showArxivTip`, `showApiWarning`) 管理提示框的可见性。
33: 2. **手动收起逻辑**：
34:    - 点击提示框任意位置即可触发关闭动作。
35:    - 提示框在鼠标悬停（Hover）时显示关闭图标（`X`），提供明确的视觉反馈。
36: 3. **视觉动效**：通过 `animate-in fade-in zoom-in-95` 等 Tailwind 动画类，实现提示框的平滑显示与消失，确保交互不突兀。
37: 4. **生命周期**：提示状态仅在组件实例中维护，满足用户“本次重新打开页面时查看，确认后关闭”的需求。
38: 
39: ### 风险提示系统
40: - **下载耗时预期**：在 ArXiv 输入框下方显式提示下载可能占据绝大部分时间。
41: - **性能瓶颈预警**：在高级配置右侧增加琥珀色警告（Amber Badge），告知英伟达免费 API 的局限性，并建议自定义 API。

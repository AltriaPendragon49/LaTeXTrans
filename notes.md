# Notes

## Findings
- 废案不是完整社区，而是“论文浏览 + 翻译平台”；新系统当前也仍然是翻译工作台。
- 当前前端已有 `/`、`/processing`、`/preview`、`/history`、`/settings`、`/profile`、`/login`，尚无社区 feed、论文详情和治理页面。
- 当前后端能力集中在上传、arXiv 拉取、翻译、SSE、历史、设置、下载；社区表结构仍未建立，仓库里仅看到一条 migration。
- `texts/社区实施路线.md` 的方向正确：坚持 paper-first、翻译内嵌、下载受控、文件本地落盘。
- 但它把 Redis + Celery、通知、治理、AlphaXiv 都压进两周，作为完整交付过于乐观。

## Risks
- 误把“论文平台”当“完整社区”会导致范围失控。
- 当前任务运行态仍部分在内存中，若同时推进社区与分布式队列，容易两头失焦。
- 本地文件落盘短期可行，但若没有资产抽象与下载网关，后续迁移成本会增大。
- RLS、管理角色、下载权限若不先定边界，后续返工概率高。

## Plan Drafting Heuristics
- 先做 paper-first 的最小社区骨架。
- 先闭环主链路，再补互动、热榜、治理。
- 两周计划必须包含可验收产物、依赖与风险控制。
- 默认走 `Supabase + FastAPI` 主路径；Redis/Celery 只做可插拔预留，不作为首周阻塞项。

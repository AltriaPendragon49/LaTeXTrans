<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.
<!-- OPENSPEC:END -->

# Project Overview

LaTeX paper translation system based on RAG + Multi-Agent collaboration.

- **Backend:** Python 3.10+, FastAPI, LangChain, ChromaDB, Redis
- **Frontend:** React 18+, TailwindCSS, Vite
- **LLM:** Gemini (primary), GPT (fallback)
- **LaTeX:** MiKTeX via Docker
- **Key constraint:** Must use `pylatexenc` for AST parsing; regex forbidden for LaTeX structure

# Claude Code Capability Mapping

When you need to do this → use this Claude Code capability:

| Scenario | Claude Code |
|---|---|
| Security review | Built-in `security-review` skill |
| Code review / PR review | Built-in `review` skill |
| Brainstorming / design refinement | `EnterPlanMode` |
| Parallel independent tasks | `Agent` tool (multiple in one message) |
| Framework docs lookup | `mcp__context7` |
| General docs / research | `WebSearch` + `WebFetch` |
| Git worktree isolation | `EnterWorktree` / `ExitWorktree` |
| Simplify/improve code | Built-in `simplify` skill |

# Domain Skills

When tasks match these domains, invoke the skill via the `Skill` tool:

## Project-Specific（本项目专属）

- **`latex-translation-debugging`** — LaTeX 翻译 pipeline 失败/性能回归排查
- **`core-pool-curation-sync`** — 服务器同步 arXiv ID 核心池状态文件
- **`tencent-cloud-server-ops`** — 生产服务器部署、重启、健康检查、日志

## Backend

- **`backend-patterns`** — Node.js/Express/Next.js 后端架构模式选择
- **`supabase-postgres-best-practices`** — Postgres/Supabase 查询优化、索引、RLS、锁
- **`clickhouse-io`** — ClickHouse 分析型数据库模式与优化

## Frontend

- **`frontend-design`** — 高质量前端 UI 设计，避免 AI 通用美学
- **`ui-ux-pro-max`** — UI/UX 设计参数（50 种风格、21 种配色、50 种字体配对、9 种技术栈）
- **`vercel-react-best-practices`** — React/Next.js 性能优化（渲染、异步、打包、客户端）
- **`i18n-engineering`** — 前端国际化治理：语义化 key、禁止硬编码文案、合并门禁
- **`coding-standards`** — TypeScript/JavaScript/React/Node.js 通用编码规范
- **`component-fixtures`** — 组件截图测试 fixtures 编写

## Testing

- **`playwright-cli`** — 浏览器自动化测试、Playwright 测试编写

## Workflow

- **`tdd-workflow`** — 测试驱动开发（TDD）工作流，要求 80%+ 覆盖率
- **`skill-creator`** — 创建或更新技能

# OpenSpec Workflow

## When to propose (行为变更)

New features, architecture changes, breaking changes, security/performance behavior changes:

1. Use `EnterPlanMode` to refine the design
2. Read `openspec/AGENTS.md` for the full workflow
3. Create proposal (`proposal.md`, `tasks.md`, optional `design.md`, spec deltas)
4. Validate: `openspec validate <change-id> --strict --no-interactive`
5. Do NOT implement until proposal is approved
6. After approval, implement sequentially following `tasks.md`

## When to skip proposal (行为保持)

Bug fixes restoring intended behavior, test-only changes, non-breaking config, behavior-preserving refactors:

1. Use relevant execution skill directly
2. Verify and review before completion

# Execution Discipline

## Think Before Coding
Identify the user goal, minimal files involved, expected behavior, and verification check before editing.

## Simplicity First
Prefer the simplest change. Avoid unnecessary abstractions, new dependencies, subsystem rewrites, or scope expansion.

## Surgical Changes
Keep modifications narrow. Don't rewrite unrelated files, reformat without need, or mix cleanup with feature/bug-fix work.

## Goal-Driven Execution
Every step connects to the user's goal. Verify the requested behavior is implemented before declaring completion.

## Preserve Existing Contracts
Maintain compatibility with existing APIs, DB schema, task states, frontend props, persisted data, and public routes. Inputs and outputs must stay equivalent for behavior-preserving refactors.

## Avoid Hidden Scope Expansion
A backend bug fix should not trigger a frontend redesign. A config update should not alter runtime behavior beyond the stated goal.

## Verify Before Completion
Verification proportional to the change:
- Small config/copy: targeted inspection
- Frontend change: build, typecheck, relevant tests, or browser check
- Backend change: unit tests, integration tests, compile check, API health check
- DB/migration: migration dry-run or clear manual verification path

If verification cannot be run, state exactly what was not run and why.

# Backend Index Discipline

- When the task needs backend file lookup, read `backend/file.md` first
- If any backend production file is added, deleted, moved, or renamed, update `backend/file.md` in the same change
- Use Chinese in UTF-8 for descriptions in `backend/file.md`

# Skill Priority

1. User safety and repository security
2. OpenSpec boundary rules
3. Claude Code capability mapping (use built-in before external)
4. Domain skills via `Skill` tool when task matches
5. Backend index discipline
6. Execution discipline

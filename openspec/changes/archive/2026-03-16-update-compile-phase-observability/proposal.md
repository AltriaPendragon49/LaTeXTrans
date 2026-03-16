# Change: Update Compile Phase Observability

## Why
- 工作区审计显示，除已归档的 `support-global-ui-language` 外，唯一仍未被稳定规范覆盖的行为漂移是编译阶段可观测性。
- 当前 `GeneratorAgent` 会在真正进入编译信号量竞争前就上报 `Waiting for compile slot`，把 `find_main_tex_file()` 与 `validate_project_structure()` 的耗时伪装成排队等待，容易误导前端和运维判断。
- `validate_project_structure()` 缺少独立的阶段可见性与时长记录，导致“结构校验”“等待编译槽位”“正在编译”三种状态在体验和诊断上混在一起。
- 如果不把这部分行为单独建成 OpenSpec change，后续实现或重构时容易遗漏这套运行时语义。

## What Changes
- **ADDED** 编译阶段可观测性要求，明确只有在共享编译信号量确实不可立即获取时，才允许上报等待编译槽位状态。
- **ADDED** 结构校验阶段的外显状态和时长记录要求，用于区分 precompile validation 与 compile queue wait。
- **DOCUMENTED** 本次工作区审计结论：`frontend/coverage/` 属于生成产物噪音，不属于 OpenSpec 行为建模范围。

## Impact
- Affected specs:
  - `specs/latex-translation-core/spec.md`
  - `specs/translation-orchestration/spec.md`
- Affected code:
  - `backend/app/services/agents/generator_agent.py`
  - `backend/app/services/latex/structure_guard.py`
- Related work:
  - `openspec/changes/update-compile-queue-reporting/` 与本 change 部分重叠，后续实现前应合并或择一保留。

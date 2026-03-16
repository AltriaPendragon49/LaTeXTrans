# Workspace Unrelated Changes Audit

## Summary
- 审查基准：排除已归档的 `support-global-ui-language` 及其归档直接产物。
- 结论：当前工作区中，唯一明确需要以 OpenSpec 保留的“产品/运行时行为”主题是编译阶段可观测性漂移。

## Spec-Worthy Findings
- `backend/app/services/agents/generator_agent.py` 目前会在真实进入编译信号量竞争前上报 `Waiting for compile slot`。
- `backend/app/services/latex/structure_guard.py` 的 `validate_project_structure()` 缺少独立外显阶段与时长记录。
- 这两点已整理为新 change：`openspec/changes/update-compile-phase-observability/`。

## Non-Spec Findings
- `frontend/coverage/` 属于测试生成产物噪音，不应通过 OpenSpec 建模。
- `openspec/changes/update-compile-queue-reporting/` 与新建 change 存在部分重叠，后续实现前应合并或择一保留。

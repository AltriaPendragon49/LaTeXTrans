# Design: Compile Phase Observability

## Context
工作区中除已归档的全局 UI 语言/i18n 变更外，剩余最清晰的产品级行为漂移集中在编译阶段状态上报。

当前 `GeneratorAgent` 的顺序大致为：
1. 处理排版配置
2. 提前上报 `Waiting for compile slot`
3. 定位 `main.tex`
4. 执行 `validate_project_structure()`
5. 获取编译信号量
6. 上报 `Compiling PDF document`

这个顺序会把“主文件定位失败”与“结构校验耗时”都伪装成队列等待，违背“等待编译槽位”应只表示真实资源竞争的语义。

## Goals
- 让 compile queue wait 只表示真实的 semaphore contention。
- 让 precompile structure validation 成为独立、可观察的阶段。
- 保留足够的时长指标，支持后续诊断 compile wait 和 structure guard 开销。

## Non-Goals
- 不扩展全局 UI 语言或 i18n 范围。
- 不把 `frontend/coverage/` 一类生成产物纳入 OpenSpec 行为建模。
- 不在本 change 中调整任务状态字段协议；这里只约束编译阶段状态语义。

## Target Flow
目标顺序应为：
1. 处理排版配置
2. 定位 compile-ready `main.tex`
3. 上报 `Checking project structure...`
4. 执行 `validate_project_structure()` 并记录时长
5. 若信号量当前不可立即获取，则上报 `Waiting for compile slot`
6. 获取信号量后立即切换为 `Compiling PDF document`

## State Semantics
- `Checking project structure...`：表示 deterministic precompile validation 正在执行。
- `Waiting for compile slot`：只在编译信号量已耗尽、任务实际阻塞等待时出现。
- `Compiling PDF document`：表示已进入实际编译执行区间，不再包含前置校验耗时。

## Telemetry
- 结构校验时长应单独记录，避免与 compile queue wait 或 compile execution 混淆。
- compile queue wait 时长仍然保持独立统计，便于定位是“前置校验慢”还是“编译资源不足”。

## 1. Specification
- [x] 1.1 为 `latex-translation-core` 添加真实编译队列等待语义
- [x] 1.2 为 `translation-orchestration` 添加结构校验可见性与时长要求
- [x] 1.3 将 `update-compile-queue-reporting` 的重叠内容并入并清理旧草案

## 2. Implementation
- [x] 2.1 将 `Waiting for compile slot` 移到真实等待信号量的边界
- [x] 2.2 在 `validate_project_structure()` 前增加独立状态上报
- [x] 2.3 为结构校验增加独立时长日志

## 3. Verification
- [x] 3.1 运行 `openspec validate update-compile-phase-observability --strict --no-interactive`
- [x] 3.2 验证单任务无竞争时不会误报 compile queue waiting
- [x] 3.3 验证结构校验阶段与真实编译等待可在日志/状态中区分

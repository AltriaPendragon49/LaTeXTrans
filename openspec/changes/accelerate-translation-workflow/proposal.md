# Change: accelerate-translation-workflow

## Why
当前 LaTeX 翻译工作流在处理结构损坏（如特殊字符、环境封闭错误等）时，容易陷入无限重试、由于大范围失败路径引发的等待阻塞（如长时间 API 睡眠）等问题，严重影响处理效率和系统稳定性。通过引入严格的受限状态机和一次性结构修复机制，可以在确保结构安全优先的前提下，彻底杜绝无限重试与阻塞问题，显著缩短单篇论文的整体翻译和处理时间。

## What Changes
- **引入阶段 0：结构不变量检测**：前置检测未转义的 `$` 或 LaTeX 结构 token 泄露，用于状态分流。
- **引入阶段 1：普通翻译路径**：针对安全的 env 直接翻译，无额外修复。
- **引入阶段 2：受控 LLM 修复尝试**：针对检测到存在危险的 env，尝试不超过1次的纯结构性 LLM 修复（仅封装、转义、placeholder 替换，禁止翻译或改写语义内容）。失败则立刻终止 LLM 路径。
- **引入阶段 3：决定性降级**：对于无法通过修复的危险 env，强制选择原文直出、规则翻译或 placeholder + 注释输出，保证一次性输出安全结构。
- **并发资源控制与重试限制**：正常 env 并发执行，危险 env 串行执行。限制 API HTTP 429 等限流错误单 env 最多允许 1 次等待。杜绝无限重试。

## Impact
- Affected specs: `ControlledRepairWorkflow`.
- Affected code:
  - `backend/app/services/translation/dispatcher.py` [UPDATE]
  - `backend/app/services/translation/repairer.py` [NEW]
  - `backend/app/services/translation/downgrade.py` [NEW]

# Tasks: Enhance LaTeX Compiler

## Overview

增强 LaTeX 编译器，添加三引擎智能编译和 PDF 生成确认机制。

## Task List

### Phase 1: 三引擎智能编译

- [x] **1.1** 添加语言检测函数 `detect_document_language()`
  - 文件: `backend/app/services/latex/compiler.py`
  - 输入: .tex 文件路径
  - 输出: "cjk" 或 "latin"
  - 检测中文/日文/韩文字符

- [x] **1.2** 添加 LuaLaTeX 编译支持
  - 文件: `backend/app/services/latex/compiler.py`
  - 修改 `compile_latex()` 函数支持 `engine="lualatex"`
  - 验证 latexmk 对 LuaLaTeX 的调用参数

- [x] **1.3** 重构 `compile_with_fallback()` 为 `compile_with_intelligent_fallback()`
  - 文件: `backend/app/services/latex/compiler.py`
  - 新增可选参数 `preferred_order`
  - 实现智能引擎顺序选择
  - 保留现有的重试、取优、保底逻辑

- [x] **1.4** 更新 `LaTeXCompiler` 类调用新函数
  - 文件: `backend/app/services/latex/compiler.py`
  - 确保向后兼容

### Phase 2: PDF 生成确认机制

- [x] **2.1** 添加 PDF 就绪验证函数 `verify_pdf_ready()`
  - 文件: `backend/app/services/latex/compiler.py`
  - 检查文件存在、大小、可读性
  - 验证 PDF 文件头

- [x] **2.2** 在 CoordinatorAgent 中添加 PDF 验证
  - 文件: `backend/app/services/agents/coordinator_agent.py`
  - 在 `shutil.move()` 后调用验证函数
  - 确保文件完全就绪后才更新进度

- [x] **2.3** 增强翻译任务状态更新
  - 文件: `backend/app/api/routes/translate.py`
  - 添加 PDF 完整性验证
  - 可选：添加 `pdf_ready` 字段到任务状态

- [x] **2.4** 增强预览接口的错误处理
  - 文件: `backend/app/api/routes/download.py`
  - 添加 PDF 文件大小和头验证
  - 返回 503 状态码用于重试场景

### Phase 3: 规范更新

- [x] **3.1** 更新 LaTeX 编译规范
  - 文件: `openspec/specs/latex-translation-core/spec.md`
  - 添加 LuaLaTeX 相关场景
  - 添加智能语言检测场景
  - 更新编译策略描述

### Phase 4: 验证

- [x] **4.1** 单元测试：语言检测（语法检查通过）
  - 测试中文、日文、韩文、英文文档检测

- [x] **4.2** 集成测试：三引擎编译（语法检查通过）
  - 测试编译顺序根据语言变化
  - 测试后备机制

- [ ] **4.3** 手动验证：PDF 预览（用户手动测试）
  - 快速点击预览按钮测试
  - 验证不出现 404/500 错误

- [ ] **4.4** 手动验证：翻译流程（用户手动测试）
  - 翻译中文文档，检查编译日志
  - 翻译英文文档，检查编译日志

## Dependencies

- 任务 1.3 依赖 1.1, 1.2
- 任务 2.2 依赖 2.1
- Phase 2 可与 Phase 1 并行开发
- Phase 3 在 Phase 1+2 完成后进行
- Phase 4 在所有实现完成后进行

## Estimated Time

- Phase 1: 1 小时
- Phase 2: 30 分钟
- Phase 3: 15 分钟
- Phase 4: 30 分钟

**总计**: 约 2.5 小时

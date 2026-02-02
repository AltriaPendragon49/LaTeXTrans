# Proposal: Enhance LaTeX Compiler

## Change ID
`enhance-latex-compiler`

## Status
**Implemented** | Created: 2026-02-02 | Implemented: 2026-02-02

## Summary
增强 LaTeX 编译器系统，添加 LuaLaTeX 支持、智能语言检测机制，并修复 PDF 预览时机问题。

## Problem Statement

### 问题 1：编译器引擎选择不够智能
当前系统采用固定的 `pdflatex → xelatex` 编译顺序。对于翻译为中文/日文/韩文等 CJK 语言的文档，应该优先使用对 Unicode 和现代字体支持更好的引擎。

**现状**：
- 固定顺序：pdflatex 优先，xelatex 后备
- 缺少 LuaLaTeX 支持
- 对于翻译后的中文文档，pdflatex 可能产生字体/编码问题

**用户反馈**：
> "这篇译文 PDF 是 pdflatex 编译的，默认采用 xelatex 效果是不是更好？有没有必要加上 LuaLaTeX？"

### 问题 2：PDF 预览时机问题
用户点击 "View PDF" 过快时，可能因为 PDF 文件尚未完成复制/重命名导致无法显示。

**现状**：
- `coordinator_agent.py` 在 `shutil.move()` 后立即更新进度为 100%
- `translate.py` 检测到 PDF 存在后立即更新任务状态为 COMPLETED
- 前端收到 COMPLETED 状态后立即允许预览
- 可能存在文件系统缓冲导致的竞态条件

## Proposed Solution

### 解决方案 1：三引擎智能编译策略

1. **添加 LuaLaTeX 支持**
   - 在现有 pdflatex/xelatex 基础上添加 LuaLaTeX 作为第三个编译引擎
   - LuaLaTeX 对 Unicode 有更好的原生支持，适合复杂多语言文档

2. **智能语言检测**
   - 扫描翻译后的 `.tex` 文件内容
   - 检测 CJK 字符（中文、日文、韩文）占比
   - 根据检测结果动态调整编译顺序

3. **编译顺序策略**
   - **CJK 文档**（非拉丁字符 > 100）：`XeLaTeX → LuaLaTeX → PDFLaTeX`
   - **拉丁文档**（非拉丁字符 ≤ 100）：`PDFLaTeX → XeLaTeX → LuaLaTeX`

4. **保留现有机制**
   - ✅ 保留重试机制（每个引擎尝试编译）
   - ✅ 保留取优机制（选择 error 最少的 PDF）
   - ✅ 保留保底机制（全部无 PDF 则提供 tex 源文件下载）
   - ✅ 保留 latexmk 智能构建

### 解决方案 2：PDF 生成完成确认机制

1. **文件完整性验证**
   - 在 `shutil.move()` 后添加文件存在性和可读性验证
   - 确保文件句柄已完全释放

2. **任务状态同步**
   - 只有在 PDF 文件验证通过后才更新任务状态为 COMPLETED
   - 添加 `pdf_ready` 标记到任务信息中

3. **预览接口增强**
   - 预览接口检查 `pdf_ready` 标记
   - 如果 PDF 未就绪，返回有意义的等待提示

## Affected Components

| Component | Change Type | Description |
|-----------|-------------|-------------|
| `backend/app/services/latex/compiler.py` | MODIFIED | 添加 LuaLaTeX 支持、语言检测 |
| `backend/app/services/agents/coordinator_agent.py` | MODIFIED | PDF 复制完成验证 |
| `backend/app/api/routes/translate.py` | MODIFIED | 任务状态同步 |
| `backend/app/api/routes/download.py` | MODIFIED | 预览接口增强 |
| `openspec/specs/latex-translation-core/spec.md` | MODIFIED | 更新编译规范 |

## Technical Design

见 [design.md](./design.md) - 详细技术设计

## Verification Plan

### 自动化测试
1. 单元测试：语言检测函数的准确性
2. 单元测试：LuaLaTeX 编译调用
3. 集成测试：三引擎后备链路

### 手动验证
1. 编译中文翻译文档，验证 XeLaTeX 优先生效
2. 编译英文文档，验证 PDFLaTeX 优先生效
3. 快速点击 "View PDF" 按钮，验证不会出现预览失败
4. 测试编译失败时的源文件下载功能

## Timeline

- 预计实现时间：2-3 小时
- 无外部依赖

## Open Questions

无

## References

- 现有编译器代码：`backend/app/services/latex/compiler.py`
- 现有规范：`openspec/specs/latex-translation-core/spec.md`

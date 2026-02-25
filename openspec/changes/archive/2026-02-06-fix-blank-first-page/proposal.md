# fix-blank-first-page

## Status
IMPLEMENTING

## Problem Statement
论文 2508.18791 翻译后生成的 PDF 第一页为空白。通过分析编译日志发现根因：

```
./acl_latex.tex:3: Undefined control sequence.
l.3 \pdfoutput=1
```

`\pdfoutput=1` 是 **pdfLaTeX 专用命令**，在系统使用 **XeLaTeX** 编译中文文档时该命令未定义，导致编译错误并产生空白第一页。

### Root Cause Analysis
1. 原始 arXiv 论文常包含 `\pdfoutput=1` 以确保 pdfLaTeX 输出 PDF 格式
2. 我们的系统使用 XeLaTeX 编译中文翻译（因为需要 ctex 包）
3. XeLaTeX 不识别 `\pdfoutput` 命令，但编译器以 `nonstopmode` 继续执行
4. 这个错误发生在 `\documentclass` 之前，导致第一页被异常处理

### Current Code Analysis
`reconstruct.py` 中存在 `_comment_out_latex_packages_for_ja()` 函数，用于日语支持时注释掉冲突包：
```python
packages_to_comment = [
    r'\usepackage[utf8]{inputenc}',
    r'\usepackage[T1]{fontenc}',
    r'\usepackage{times}',
    r'\usepackage{mathptmx}',
    r'\pdfoutput=1'  # 已包含在列表中
]
```

但该函数**仅用于日语支持**（当前被注释掉），中文支持的 `add_ctex_package()` 没有处理这些冲突命令。

## User Review Required

> [!IMPORTANT]
> 此修复将自动注释掉 `\pdfoutput=1` 命令。这可能影响其他依赖该命令的工作流程。

## Proposed Changes

### [MODIFY] [reconstruct.py](file:///d:/future/antigravity/LaTexTrans/backend/app/services/latex/reconstruct.py)

1. 新增 `_comment_out_pdflatex_specific_commands()` 方法，专门处理在 XeLaTeX 编译时需要注释的命令：
   - `\pdfoutput=1`
   - 可选：其他 pdfLaTeX 特定命令

2. 在 `_revert_inputs()` 方法中的 `add_ctex_package(tex)` 后调用此新方法

### [MODIFY] [utils.py](file:///d:/future/antigravity/LaTexTrans/backend/app/services/latex/utils.py)

1. 增强 `add_ctex_package()` 函数，在添加 ctex 包后也处理 `\pdfoutput=1`
2. 或者创建新的 `clean_for_xelatex()` 函数统一处理

## Verification Plan

### Manual Verification
1. 使用 arXiv ID `2508.18791` 重新执行翻译流程
2. 检查生成的 `acl_latex.tex` 文件，确认 `\pdfoutput=1` 被注释
3. 验证编译后的 PDF 第一页不再为空白

### 编译日志检查
1. 查看 `acl_latex.log` 确认不再有 `Undefined control sequence` 错误

## Dependencies
- 无新增依赖

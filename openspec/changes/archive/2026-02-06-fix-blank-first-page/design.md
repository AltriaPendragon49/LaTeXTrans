# fix-blank-first-page Design

## Architectural Overview

### Problem Flow
```
Original LaTeX → Contains \pdfoutput=1 → XeLaTeX compilation → Undefined command error → Blank first page
```

### Solution Flow
```
Original LaTeX → Reconstruction → Comment out \pdfoutput=1 → XeLaTeX compilation → Correct output
```

## Implementation Details

### Option 1: Modify add_ctex_package() (Recommended)

在 `utils.py` 中的 `add_ctex_package()` 函数末尾添加对 `\pdfoutput` 的处理：

```python
def add_ctex_package(latex_code):
    """Add ctex package for Chinese support"""
    if "\\usepackage[UTF8]{ctex}" not in latex_code:
        ctex_package = "\\usepackage[UTF8]{ctex}"
        documentclass = r'documentclass'
        documentclass_pattern = get_command_pattern(documentclass)
        match = documentclass_pattern.search(latex_code)
        if match:
            position = match.end()
            latex_code = latex_code[:position] + "\n" + ctex_package + "\n" + latex_code[position:]
    
    # 处理 pdflatex 特定命令，在 xelatex 编译时需要注释掉
    latex_code = _comment_out_pdflatex_commands(latex_code)
    
    return latex_code


def _comment_out_pdflatex_commands(latex_code: str) -> str:
    """Comment out pdfLaTeX-specific commands that conflict with XeLaTeX"""
    import re
    
    # 匹配 \pdfoutput=1 或 \pdfoutput = 1 等变体
    # 只注释掉未被注释的行
    pattern = re.compile(r'^(?!%)(\\s*\\\\pdfoutput\\s*=\\s*\\d+)', re.MULTILINE)
    latex_code = pattern.sub(r'% \\1  % Commented for XeLaTeX compatibility', latex_code)
    
    return latex_code
```

### Option 2: Add to reconstruct.py

在 `LatexConstructor` 类中添加独立方法，参考现有的 `_comment_out_latex_packages_for_ja()`。

## Edge Cases

1. **已注释的命令**：不重复注释
2. **变体格式**：处理 `\pdfoutput = 1`、`\pdfoutput=0` 等
3. **多次出现**：处理文档中多次出现的情况

## Performance Impact

- 字符串替换操作，对性能影响可忽略

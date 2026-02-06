# fix-blank-first-page Tasks

## Implementation Tasks

- [x] 在 `utils.py` 添加 `_comment_out_pdflatex_commands()` 函数
- [x] 修改 `add_ctex_package()` 调用新函数

## Verification Tasks

- [x] 手动测试：重新翻译 arXiv 2508.18791
- [x] 验证 PDF 第一页不再空白
- [x] 检查编译日志无 `Undefined control sequence` 错误

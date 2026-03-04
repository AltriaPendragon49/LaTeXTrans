# Tasks: LaTeX Sanitization Layer

## Phase 1: Basic Image Sanitizer (Completed)
- [x] **Compiler Regex**: Update `parse_log_errors` to handle `(` and multi-line splits.
- [x] **Trigger Logic**: Trigger Stage 3 before returning best-effort results.
- [x] **GS Path Robustness**: Add hardcoded installation path fallbacks for Windows.
- [x] **Multi-file Patching**: Recursively scan and patch all `.tex` files in the project.

## Phase 2: Iterative Repair Loop (Completed)
- [x] **接口升级**: `sanitizer.py` 支持 `already_sanitized` 并返回 3-tuple。
- [x] **循环重写**: `compiler.py` 实现 `MAX_SANITIZE_ROUNDS` 迭代循环。
- [x] **短路逻辑**: 实现基于“无新发现”和“无错误”的自动退出。
- [x] **单引擎策略**: 循环内固定使用 Stage 2 最佳引擎以节省时间。

## Phase 3: Pre-Compile Sanitization (Completed)
- [x] **Rules Model**: Define `CONFLICT_RULES` for `axessibility`, `accsupp`, etc.
- [x] **Sanitizer Hook**: Build `apply_precompile_sanitization` in `sanitizer.py`.
- [x] **Compiler Integration**: Call the hook in `compiler.py` before Stage 1.
- [x] **Verification**: Pass unit tests for package filtering.

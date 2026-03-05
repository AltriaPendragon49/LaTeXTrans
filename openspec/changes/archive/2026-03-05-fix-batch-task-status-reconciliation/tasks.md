# Tasks

## 1. 修复 history endpoint 惰性推断输出路径
- [x] 修改 `backend/app/api/routes/history.py`：当 `output_path` 为空时，用 `settings.outputs_dir / task["task_id"]` 兜底推断路径
- [x] 同时将推断出的 `output_path` 也写入 Supabase correction

## 2. 提早写入 output_path (translate.py)
- [x] 修改 `backend/app/api/routes/translate.py` 中的 `run_translation`，在 `output_dir.mkdir()` 后立刻通过 `update_task` 写入 `output_path`

## 3. 验证与更新 tasks.md
- [x] 确认所有修改正确，更新 openspec tasks.md 所有项目为 [x]

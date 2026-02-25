# Runtime Config Capture Testing Guide

```bash
# 1) Enter backend workspace
cd backend

# 2) Ensure runtime config capture is enabled (default: true)
set ENABLE_TASK_CONFIG_CAPTURE=true

# 3) Start backend and run translation tests from frontend

# 4) Verify captured snapshots
dir data\\task_configs

# 5) Validate captured configs
python tests/config_validator.py data/task_configs/config_*.json
```

Notes:
- Runtime capture is integrated in `translate.py` and does not depend on `backend/tests/test_config_interceptor.py`.
- `python tests/apply_interceptor_patch.py` is only a compatibility helper for older branches.

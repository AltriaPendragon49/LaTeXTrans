# Design: update-failed-task-quarantine

## Context
The system persists authenticated task records in Supabase (`translation_tasks`) and maintains in-memory state in `TaskManager`.  
Historically:
- failed tasks stayed in persistent history
- failed outputs stayed mixed in regular output directories
- config capture depended on importing `backend.tests.test_config_interceptor` at runtime

This change solves both operational problems:
1. failed-task quarantine + history cleanup  
2. runtime-safe config capture under `backend/data/task_configs`

## Goals / Non-Goals
- Goals:
  - quarantine failed output artifacts for easier debugging
  - remove failed tasks from persistent history rows
  - keep in-memory status visibility for active polling
  - keep cancellation behavior unchanged (cancelled tasks are excluded)
  - capture runtime translation configs without test-module dependency
  - keep translation flow fail-open when capture cannot be written
- Non-Goals:
  - no external API schema change
  - no migration of `terms` or `uploads` in failed-task quarantine
  - no database schema migration
  - no automatic retention cleanup for `task_configs`

## Decisions
- Decision: keep failed-task interception centralized in `TaskManager.update_task()`.
  - Why: this is the canonical status transition point.
- Decision: move only `outputs/{task_id}` into `failed_tasks`.
  - Why: preserves debug evidence while avoiding unnecessary data movement.
- Decision: runtime Supabase delete on failure terminal states.
  - Why: immediate history cleanup without deferred jobs.
- Decision: preserve in-memory failed task after delete.
  - Why: avoids breaking live task polling.
- Decision: skip failed-task quarantine/delete for cancelled tasks.
  - Why: cancellation is user intent, not failure triage.

- Decision: implement config capture as runtime service module.
  - Why: removes fragile dependency on `backend.tests`.
- Decision: gate config capture with `ENABLE_TASK_CONFIG_CAPTURE` (default `true`).
  - Why: supports production-safe default testing while retaining explicit off switch.
- Decision: sanitize snapshot payload and mask API keys.
  - Why: protects secrets in persisted debug artifacts.
- Decision: use atomic write (`.tmp` then replace) and fail-open error handling.
  - Why: avoid partial files and never block translation.

## Data Flow
1. `translate.py` builds `llm_config` and `agent_config`.
2. `capture_task_config(...)` is called with:
  - `task_id`
  - `advanced_config`
  - `agent_config`
  - `llm_config`
  - additional runtime metadata
3. `config_capture` service checks `enable_task_config_capture`:
  - if disabled -> return `None`
  - if enabled -> write `config_<task8>_<timestamp>.json` into `task_configs_dir`
4. translation continues regardless of capture outcome.

For failed tasks:
1. `TaskManager.update_task()` sees status in `{failed, failed_compilation}`.
2. if not cancelled and not already intercepted:
  - move output directory to `failed_tasks`
  - delete Supabase row in `translation_tasks`
  - set in-memory `failure_intercepted=True` and update `failed_output_path`
3. continue terminal notification flow.

## Failure Handling
- Config capture write failure:
  - log warning
  - return `None`
  - translation continues
- Failed-task quarantine errors:
  - log error
  - do not raise to caller
- Supabase delete errors:
  - log error
  - do not raise to caller
- Idempotency:
  - guarded by `failure_intercepted` for failed-task interception

## Compatibility
- `GET /api/history` no longer returns auto-intercepted failed tasks (row deleted).
- `GET /api/task/{task_id}` can still return in-memory failed task while service is alive.
- Config capture no longer relies on `backend/tests` modules.
- Existing validator workflow remains usable with new output path:
  - `python tests/config_validator.py data/task_configs/config_*.json`

## Migration Plan
- No schema migration required.
- Deploy with defaults:
  - `ENABLE_TASK_CONFIG_CAPTURE=true`
- Monitor logs for:
  - capture success/failure
  - failed-task quarantine moves
  - Supabase delete success/failure

## Risks / Trade-offs
- Risk: capture files can accumulate without cleanup.
  - Mitigation: accepted by design for current debugging needs.
- Risk: Supabase transient outage can leave failed rows undeleted.
  - Mitigation: non-blocking behavior with clear logs; manual cleanup possible.
- Risk: local filesystem write errors can skip capture.
  - Mitigation: fail-open with warnings, no task interruption.

# Change 跟进报告: `replace-supabase-with-niutrans-auth-and-mysql`

日期: 2026-04-09  
审阅提交: `41725f93cf9713525c500882b3de0c4088600ef2`  
用途: 记录这次最新实现实际完成了什么、审阅与研究发现了什么、后续应如何继续推进该 OpenSpec change。

## 1. 结论摘要

这次提交确实把 change 往前推进了一大步，主要落在 3 个方面:

- 建立了第一版可用的本地认证基础设施: NiuTrans 凭证校验 + 本地 JWT/Session
- 建立了第一版 MySQL/本地持久化基础设施: 连接层、迁移脚本、核心表结构、仓储层
- 把 `user_settings` 从 Supabase RLS 模式迁到了本地仓储模式

但这次提交还没有完成 change 目标里承诺的完整切换，当前代码处于明显的“半迁移”状态:

- 认证和设置部分已经开始走本地链路
- `translation_tasks` 的运行时持久化、历史记录查询、启动期修复和清理逻辑仍然依赖 Supabase
- 某些兼容性回退逻辑带来了安全和正确性风险

因此，这次提交更适合被定义为“认证/设置与本地持久化基础设施已落地”，而不是“`translation_tasks/history` 已完成 MySQL 化”。

## 2. 本次提交实际做了什么

### 2.1 本地认证链路落地

新增了以下接口:

- `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/auth/logout`

新增的核心实现包括:

- `LocalAuthService`
- `AuthRepository`
- 本地 JWT 签发与校验逻辑
- `users`、`user_roles`、`auth_sessions` 的本地会话与用户映射
- `optional_current_user`、`require_current_user`、`require_admin_user` 依赖

整体行为是:

- 前端把账号密码发给后端
- 后端调用 NiuTrans 登录接口校验凭证
- 校验成功后，在本地创建或更新映射用户
- 生成本地 JWT，并创建本地 session 记录
- `/me` 使用本地 token + session 进行 bootstrap
- `/logout` 撤销当前 session

### 2.2 本地数据库与迁移基础设施落地

新增了:

- `backend/app/db/connection.py`
- `backend/scripts/apply_mysql_migrations.py`
- `backend/migrations_mysql/20260409_0001_local_auth_mysql.sql`
- MySQL 运行依赖与配置项

本次迁移文件已经定义了这些表:

- `users`
- `user_roles`
- `auth_sessions`
- `user_settings`
- `translation_tasks`
- `papers`
- `paper_assets`
- `community_conversations`
- `community_conversation_turns`
- `community_agent_runs`
- `community_agent_events`

这说明目标 schema 已经有了初版骨架，后续继续迁移时有了明确落点。

### 2.3 `user_settings` 已迁到本地仓储

这是本次提交里完成度最高的部分。

`/api/settings` 已经从“Supabase + RLS”改成:

- 使用 `require_current_user`
- 使用 `UserSettingsRepository`
- 使用 `USER_SETTINGS_DEFAULTS`
- 保留自定义 API Key 的加密写入逻辑

从行为上看，这部分已经基本符合 OpenSpec 对本地认证 + 本地持久化的方向。

### 2.4 相关路由开始接入新认证依赖

以下路由已接入新的认证解析逻辑:

- `upload.py`
- `arxiv.py`
- `translate.py`
- `main.py` 中的 auth router 注册

这些改动主要是为了:

- 给上传/下载/翻译任务挂接用户身份
- 兼容 guest 与 authenticated 两种调用路径
- 为后续彻底移除 Supabase 用户态链路做铺垫

### 2.5 新增了配套测试

新增测试文件:

- `backend/tests/unit/test_local_auth_api.py`
- `backend/tests/unit/test_local_auth_service.py`
- `backend/tests/unit/test_local_user_settings_api.py`

测试覆盖方向包括:

- 本地 auth API 的返回契约
- 本地 auth service 的登录/校验/登出回路
- 本地 settings API 的读取与更新行为

## 3. 对照 `tasks.md` 的进度判断

结合代码实际状态，这次提交对 OpenSpec 任务的推进可以分成 3 类。

### 3.1 明确已推进

- `1.1` 后端登录/登出/bootstrap 接口
- `1.2` 本地 JWT/session 契约
- `1.3` 本地 token 校验与 current-user 依赖
- `1.5` 基于 NiuTrans `userId` 的本地用户映射与 admin seed 策略
- `2.1` MySQL 连接、迁移工作流与基础仓储/服务辅助层
- `3.2` `user_settings` 从 Supabase 迁移到 MySQL
- `6.1` 本地登录链路的第一轮验证

### 3.2 有推进，但还不能算完成

- `2.2` MySQL DDL/索引/约束策略
  - 已有初版 DDL，但运行时采用并不完整
- `2.3` 运行时 Supabase 路径替换为 MySQL 仓储
  - 只完成了 auth/settings 的一部分
- `3.1` `translation_tasks` 持久化/历史/删除/修复迁移
  - 提交信息写到了这一点，但实际主链路仍未完成切换
- `6.3` 验证 authenticated history/settings 是否已跑在 MySQL
  - settings 可以
  - history 还不行

### 3.3 本次提交尚未覆盖

- `1.4` 统一授权入口 `authorize(...)`
- `1.6` 前端本地 auth 状态管理替换
- `1.7` 登录/注册/找回相关 UI 跳转改造
- `3.3` guest translation 完整保留验证
- `3.4` batch translation 的 MySQL 语义迁移
- `4.x` 社区相关迁移
- `5.x` 数据迁移与回滚/校验工作
- `6.2` `6.4` `6.5` 更广泛的本地验证

## 4. 审阅与研究结果

### 4.1 高优先级问题: 可选认证回退会接受未验签的 `sub`

这次提交里最需要尽快修的风险在 `backend/app/core/auth.py`。

当前链路是:

- `optional_current_user()` 先尝试用 `LocalAuthService` 校验 token
- 如果失败，某些路由仍会继续调用 `resolve_current_user_id()`
- `resolve_current_user_id()` 会回退到 `decode_unverified_sub_claim()`
- `decode_unverified_sub_claim()` 只是 base64 解码 payload，并直接取出 `sub`

也就是说，只要传一个“长得像 JWT”的伪 token，就可能把伪造的 `sub` 当成 `user_id` 使用。

影响面包括:

- 上传任务归属
- arXiv 下载任务归属
- 单任务翻译归属
- 队列额度统计
- 用户自定义 API 配置读取路径

影响性质:

- 会污染任务 owner
- 会影响 quota 统计
- 会影响按用户读取配置的逻辑
- 本质上属于身份冒用风险

结论:

- 所有会写状态、算配额、读用户私有配置的路径，都不应该再接受未验签 `sub` 的回退逻辑

### 4.2 高优先级问题: 本地 JWT 仍无法真正打通历史接口

虽然本次提交已经能签发本地 JWT，但 `history.py` 仍然依赖 `get_supabase_client_from_request()`。

当前情况:

- `/api/history` 仍然通过 Supabase user-scoped client 查询
- `get_supabase_client_from_request()` 只要看到 JWT 形状的 token，就会继续构造 Supabase client
- 因此本地 token 仍会被送进旧的 Supabase 路径，而不是本地仓储路径

这意味着:

- 新登录链路并没有真正完成“历史记录切换”
- `tasks.md` 和提交信息中关于 `history` MySQL 化的表述，领先于实际代码状态

结论:

- 历史接口仍处于旧链路，必须完成真正的 repository 迁移，才能算实现了 `3.1`

### 4.3 高优先级问题: `translation_tasks` 运行时持久化仍写 Supabase

虽然 MySQL 迁移里已经定义了 `translation_tasks`，但运行时核心路径还在走 Supabase:

- `TaskManager._persist_task_create()` 仍然插入 Supabase
- `TaskManager._persist_task_update()` 仍然更新 Supabase
- `main.py` 启动时的 interrupted task 修复仍在查/改 Supabase `translation_tasks`
- orphan cleanup 仍依赖 Supabase 中是否存在 task row

这说明当前状态并不是:

- “`translation_tasks` 已经迁到 MySQL”

而是:

- “MySQL schema 已准备，但运行时任务主链路仍在 Supabase”

结论:

- 这是当前 change 距离真正 cutover 最大的缺口

### 4.4 当前整体状态: 半迁移

目前系统大致是这样的:

- auth: 开始走本地
- settings: 已基本走本地
- task persistence/history/startup cleanup: 仍大量走 Supabase

这种分阶段推进本身可以接受，但前提是文档和任务状态要准确表达“这是阶段性里程碑，而不是完整切换”。

## 5. 验证证据

### 5.1 Git 证据

审阅的提交:

- `41725f93cf9713525c500882b3de0c4088600ef2`

提交统计:

- 22 个文件变更
- 1743 行新增
- 313 行删除

主要改动集中在:

- auth route / auth service
- auth/settings repository
- 本地 DB 连接与迁移
- upload/arxiv/translate/settings 路由接线
- 新增测试
- OpenSpec `tasks.md` 勾选更新

### 5.2 本地代码验证

我在本地做了 2 个直接验证:

1. 伪造一个 payload 含 `sub=usr_victim_123` 的 JWT 形状 token，传给 `resolve_current_user_id(None, credentials)`，函数会返回 `usr_victim_123`
2. 把本地 JWT 形状 token 传给 `get_supabase_client_from_request()`，仍会得到 Supabase `Client`

这两个结果分别证明了:

- 未验签 `sub` 回退确实存在
- 历史等旧链路仍然会把本地 token 送入 Supabase client 路径

### 5.3 测试执行结果

执行命令:

```bash
pytest backend/tests/unit/test_local_auth_api.py backend/tests/unit/test_local_auth_service.py backend/tests/unit/test_local_user_settings_api.py
```

结果:

- `test_local_auth_api.py`: 通过
- `test_local_user_settings_api.py`: 通过
- `test_local_auth_service.py`: 在当前环境被本地权限问题阻塞

阻塞信息:

- `PermissionError: [WinError 5]`
- 发生在创建 `tmp_path` 时
- 目录为 `C:\Users\xhs\AppData\Local\Temp\pytest-of-xhs`

因此，这次提交的 auth service roundtrip 测试意图是有的，但在当前环境下还没有完成完整验证。

## 6. 建议的下一步

### 6.1 先修安全回退

- 去掉未验签 `sub` 作为 `user_id` 的回退逻辑
- guest 兼容路由里，token 无效就应视为未登录，而不是“半登录”
- 所有 owner/quota/user-config 读取路径都只接受已验证身份

### 6.2 完成 `translation_tasks` 与 `history` 的真正迁移

- 把 task create/update/query/delete 从 Supabase 换到 MySQL repository
- 把 `history list/detail/delete` 改成 MySQL 查询
- 把启动修复、cleanup、reconciliation 改成基于 MySQL 的实现

### 6.3 校正任务状态表达

- `1.1` `1.2` `1.3` `1.5` `2.1` `3.2` 可以保持已推进/已完成判断
- `3.1` `2.3` `6.3` 暂不应被视为完成
- 如果团队准备继续增量推进，建议把“当前是 foundation milestone，不是 full cutover”写进后续记录

### 6.4 补充验证

- 在可写 `tmp_path` 环境里重跑 `test_local_auth_service.py`
- 增加以下测试:
  - forged token 在 guest-compatible 路由中的拒绝行为
  - history 切到 MySQL 后的接口测试
  - startup reconciliation / cleanup 切到 MySQL 后的测试

## 7. 建议的进度口径

对这次提交，建议用下面这句话作为后续跟进口径:

> 本地认证与设置迁移基础已落地，但 `translation_tasks/history` 和运行时清理链路仍未完成切换。

这个口径比“已完成 MySQL 化”更贴近当前代码真实状态，也更方便安排下一批实现工作。
## 2026-04-09 Incremental Update

- Completed the `translation_tasks/history` local-persistence slice for the approved change.
- Added `TranslationTaskRepository` and switched these paths from Supabase queries to local DB access:
  - `backend/app/api/routes/history.py`
  - `backend/app/services/task_manager.py` task create/update/recovery persistence
  - `backend/app/api/routes/translate.py` config-hash update and reusable-output lookup
- Added/updated unit coverage for local history, local translation-task persistence, config-hash persistence, and repository-backed history query behavior.

### Scope Completed In This Increment

- Authenticated history list/detail/delete now resolve the current local user and query translation-task rows from the local database.
- Task persistence now upserts and updates `translation_tasks` through the repository layer instead of Supabase admin-client writes.
- Translation config-hash persistence and output-reuse lookup now query the same local persistence layer.

### Remaining Work After This Increment

- Startup failover, interrupted-task cleanup, and orphan cleanup in `backend/app/main.py` still use Supabase-backed task queries.
- `resolve_current_user_id(...)` fallback usage in some upload/arxiv/translate entry paths still deserves a follow-up cleanup so all authenticated writes rely on verified local user state only.
- Community paper / community-agent persistence migration remains pending.

## 2026-04-09 Incremental Update 2

- Completed the startup-side `translation_tasks` cleanup/reconciliation slice for the approved change.
- Extended `TranslationTaskRepository` with bulk helpers for:
  - status-based task id lookup
  - bulk task updates
  - existing task id lookup
  - task-id to status lookup
- Switched `backend/app/main.py` restart failover and orphaned-task cleanup to use the local translation-task repository for `translation_tasks` access.

### Scope Completed In This Increment

- Restart failover now marks interrupted local translation-task rows as failed through repository-backed persistence before optionally syncing related community paper state.
- Startup orphan cleanup now decides whether old output/terms directories are orphaned by querying local translation-task persistence instead of Supabase.
- Added focused restart-cleanup coverage for:
  - repository-backed interrupted-task failover
  - failover behavior when Supabase paper-sync credentials are absent
  - startup orphan cleanup using local task existence checks

### Verification Notes

- `python -m py_compile backend/app/main.py backend/app/repositories/translation_task_repository.py backend/tests/unit/test_restart_recovery_cleanup.py`
- Direct invocation of restart-cleanup test functions passed:
  - `test_reset_stale_community_tasks_purges_all_related_records`
  - `test_reset_stale_community_tasks_keeps_public_papers_even_if_non_success`
  - `test_fail_interrupted_translation_tasks_marks_failed_and_cleans_artifacts`
  - `test_fail_interrupted_translation_tasks_marks_local_rows_without_supabase`
  - `test_startup_orphan_cleanup_uses_local_translation_task_repository`
- Direct invocation of previously migrated local-persistence tests also passed:
  - `test_history_routes_use_local_current_user_and_repository`
  - `test_history_route_queries_local_repository_via_run_db_blocking`
  - `test_task_manager_persists_authenticated_tasks_to_local_database`
  - `test_task_manager_flush_updates_local_translation_task_rows`
  - `test_persist_task_if_needed_includes_config_hash`
  - `test_persist_task_if_needed_treats_duplicate_insert_as_success`
  - `test_persist_task_config_hash_updates_local_database`
  - `test_find_reusable_output_reads_local_database`

### Remaining Work After This Increment

- `translation_tasks` guest-flow semantics and batch retry/cutover items in `3.3` and `3.4` are still pending.
- `resolve_current_user_id(...)` fallback cleanup is still pending for upload/arxiv/translate entry paths.
- Community paper / community-agent persistence migration remains pending.

## 2026-04-09 Incremental Update 3

- Completed the verified-user resolution cleanup slice for the approved change.
- Removed the unverified-JWT `sub` fallback from `backend/app/core/auth.py::resolve_current_user_id(...)`.
- Kept upload/arxiv/single-translate/queue-status guest-compatible while ensuring authenticated behavior now depends on verified local `current_user` resolution only.
- Tightened batch translation so direct route usage without a verified local user now fails closed instead of deriving ownership from an unverified bearer token payload.

### Scope Completed In This Increment

- Remaining upload/arxiv/translate call sites that previously accepted `resolve_current_user_id(...)` fallback behavior now only receive a `user_id` from verified local auth state.
- Added focused regression coverage for:
  - forged JWT `sub` ignored during user-id resolution
  - guest-compatible upload/arxiv/start-translation behavior when auth verification fails
  - batch translation rejection for credentials without verified local user state
- Updated direct route unit tests to pass explicit `current_user` objects where they are modeling already-verified authentication.

### Verification Notes

- `pytest backend/tests/unit/test_verified_user_resolution.py backend/tests/unit/test_translate_community_publish_watch.py backend/tests/unit/test_batch_config_hash_persistence.py backend/tests/unit/test_local_translation_history_api.py backend/tests/unit/test_restart_recovery_cleanup.py -q`
- `python -m py_compile backend/app/core/auth.py backend/app/api/routes/upload.py backend/app/api/routes/arxiv.py backend/app/api/routes/translate.py backend/tests/unit/test_verified_user_resolution.py backend/tests/unit/test_translate_community_publish_watch.py backend/tests/unit/test_batch_config_hash_persistence.py backend/tests/unit/test_local_translation_history_api.py backend/tests/unit/test_restart_recovery_cleanup.py`
- Local pytest configuration now pins temp/runtime files under `backend/tests/.tmp_runtime` and disables the root pytest cache provider to avoid workspace-permission noise.

### Remaining Work After This Increment

- `translation_tasks` guest-flow cleanup expectations in `3.3` are still pending beyond the verified-user boundary fix.
- Batch persistence retry/cutover semantics in `3.4` still need to stop modeling Supabase-era retry assumptions.
- Community paper / community-agent persistence migration remains pending.

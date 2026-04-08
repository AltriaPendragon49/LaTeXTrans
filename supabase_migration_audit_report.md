# Supabase 使用审计报告

生成时间：2026-04-08  
项目：`LaTeXTrans`  
Supabase Project Ref：`ebfojcotiztnjmxbktta`  
Supabase URL：`https://ebfojcotiztnjmxbktta.supabase.co`

## 1. 报告目标

这份文档用于在迁移到 MySQL + 自建用户体系/权限体系之前，完整盘点当前项目对 Supabase 的实际依赖。  
重点覆盖：

- Supabase Auth 的登录、注册、OTP 验证、Session/JWT 使用方式
- 后端如何使用 anon key、service role key、RLS
- 当前线上实际存在的表、RLS policy、函数、触发器、索引、Storage、Auth 数据
- 代码中已经写好但线上尚未应用的 Supabase 对象
- 迁移到 MySQL 和自建认证/授权时必须自己补齐的能力

## 2. 结论摘要

### 2.1 Supabase 目前承担了什么

当前 Supabase 实际承担 4 类职责：

1. 用户认证与会话管理  
   前端直接用 `@supabase/supabase-js` 进行邮箱密码登录、注册、邮箱 OTP 验证、登出、Session 持久化、Access Token 刷新。

2. 用户态数据访问 + RLS  
   后端大多数“用户自己的数据”接口，并不自己校验 JWT，而是把前端 Access Token 透传给 Supabase anon-key client，然后让 Postgres RLS 基于 `auth.uid()` 自动过滤。

3. 系统级/管理级绕过 RLS  
   后端通过 `SUPABASE_SERVICE_ROLE_KEY` 创建 admin client，直接操作 `translation_tasks`、`papers`、`paper_assets` 等表，执行跨用户查询、后台清理、重启恢复、社区数据维护。

4. 社区功能数据库模型  
   社区论文、资源、评论、点赞、收藏、举报、通知、封禁、角色、对话记录都已建在 Supabase `public` schema 下。

### 2.2 当前线上最重要的事实

- 线上 `public` schema 当前实际有 13 张业务表：
  - `user_settings`
  - `translation_tasks`
  - `papers`
  - `paper_assets`
  - `paper_likes`
  - `paper_favorites`
  - `comments`
  - `reports`
  - `moderation_actions`
  - `notifications`
  - `user_roles`
  - `user_bans`
  - `community_agent_conversations`

- `auth` schema 当前有 33 个用户，31 个邮箱已确认，全部是 `email` provider，没有匿名用户，没有 MFA 因子。

- 线上没有 Supabase Edge Functions。

- 线上有 1 个 Storage bucket：`product`，但 `storage.objects` 当前为 0，代码也没有直接使用 Supabase Storage SDK。

- 代码中已存在但当前线上未落地的对象至少有两类：
  - `public.increment_paper_download_count()` 函数：代码会调用，线上不存在
  - `community_content_pool_*` 三张表：仓库有 migration，线上未应用

### 2.3 迁移到 MySQL 时必须自己接管的核心能力

必须自己实现：

- 用户表、密码哈希、邮箱注册、邮箱确认/OTP、登录、登出、Session/Refresh Token
- JWT 签发、校验、过期、刷新、服务端鉴权中间件
- 原来依赖 RLS 的“只看自己的数据”过滤逻辑
- 管理员/版主/封禁体系
- 社区表的权限判定
- 任务状态恢复、失败清理、跨用户后台维护
- 论文浏览/下载计数函数
- 原先由 `auth.uid()`、`current_user_is_admin()`、`current_user_is_banned()` 提供的数据库侧授权语义

## 3. 证据来源

### 3.1 代码侧

重点阅读了以下文件：

- `frontend/src/lib/supabase.ts`
- `frontend/src/contexts/AuthContext.tsx`
- `frontend/src/store/useStore.ts`
- `frontend/src/pages/Login.tsx`
- `backend/app/core/auth.py`
- `backend/app/core/supabase_client.py`
- `backend/app/core/config.py`
- `backend/app/api/routes/settings.py`
- `backend/app/api/routes/history.py`
- `backend/app/api/routes/translate.py`
- `backend/app/api/routes/upload.py`
- `backend/app/api/routes/arxiv.py`
- `backend/app/api/routes/papers.py`
- `backend/app/api/routes/community_agent.py`
- `backend/app/services/task_manager.py`
- `backend/app/services/paper_service.py`
- `backend/app/services/community_agent_service.py`
- `backend/app/services/community_content_pool_service.py`
- `backend/app/main.py`
- `backend/migrations/*.sql`

### 3.2 Supabase MCP 实时核对

对 live project 做了以下核对：

- `list_projects`
- `list_tables(public/auth/storage)`
- `list_migrations`
- `list_extensions`
- `get_publishable_keys`
- `get_project_url`
- `list_edge_functions`
- `get_advisors(security/performance)`
- `execute_sql` 查询：
  - `pg_policies`
  - `pg_proc`
  - `information_schema.triggers`
  - `pg_event_trigger`
  - `pg_indexes`
  - `pg_constraint`
  - `auth.users`/`auth.identities`/`auth.sessions`/`auth.refresh_tokens` 聚合信息
  - `storage.buckets`

## 4. 当前 Supabase 架构图谱

### 4.1 前端

前端直接连接 Supabase Auth：

- `frontend/src/lib/supabase.ts`
  - 使用 `VITE_SUPABASE_URL`
  - 使用 `VITE_SUPABASE_ANON_KEY`
  - `createClient(..., { auth: { autoRefreshToken, persistSession, detectSessionInUrl } })`

- `frontend/src/contexts/AuthContext.tsx`
  - `supabase.auth.getSession()`
  - `supabase.auth.onAuthStateChange(...)`
  - `supabase.auth.signInWithPassword(...)`
  - `supabase.auth.signUp(...)`
  - `supabase.auth.verifyOtp(...)`
  - `supabase.auth.signOut()`

### 4.2 前端到后端

前端通过 `getAccessToken()` 取出当前 Session 的 `access_token`，然后把它放进：

- `Authorization: Bearer <token>`

主要用于：

- `/api/settings`
- `/api/history`
- 需要登录状态的翻译/社区接口

### 4.3 后端用户态访问模式

后端的用户态 Supabase 访问集中在 `backend/app/core/auth.py`：

- 使用 `SUPABASE_URL + SUPABASE_ANON_KEY` 创建 user-scoped client
- 将前端 JWT 通过 `client.auth.set_session(access_token, "")` 注入
- 不主动解析用户，不主动校验 JWT 签名
- 依赖 Supabase/Postgres RLS 用 `auth.uid()` 控制数据可见性

这是当前系统最核心的授权模式。

### 4.4 后端系统态访问模式

后端的系统态 Supabase 访问集中在 `backend/app/core/supabase_client.py`：

- 使用 `SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY` 创建 admin client
- 用于跨用户查询、后台更新、启动清理、社区资源维护
- service role 会绕过所有 RLS

## 5. Auth / 登录 / JWT / Session 现状

### 5.1 前端登录注册能力

目前登录体系完全依赖 Supabase Auth：

- 登录：邮箱 + 密码
- 注册：邮箱 + 密码
- 邮箱验证：`verifyOtp(email, token, type='email')`
- Session 持久化：浏览器本地保存
- Access Token 自动刷新：开启

这意味着迁移后你们需要自己实现：

- 用户表
- 密码哈希
- 注册/登录
- 邮箱验证码/邮箱确认
- Refresh Token 与 Session 生命周期

### 5.2 当前线上 Auth 数据概况

根据 live project：

- `auth.users`：33 行
- 已确认邮箱用户：31
- 匿名用户：0
- Auth 级 ban：0
- `auth.identities` provider 分布：
  - `email`: 33
- `auth.sessions`：36
- `auth.refresh_tokens`：244
- `auth.mfa_factors`：0
- `auth.mfa_challenges`：0

结论：当前生产用户体系是纯邮箱密码体系，没有社交登录，也没有 MFA。

### 5.3 后端鉴权的真实模式

后端存在两种明显不同的 JWT 处理方式：

#### A. 透传给 Supabase，由 RLS 判权限

见：

- `backend/app/core/auth.py`
- `backend/app/api/routes/settings.py`
- `backend/app/api/routes/history.py`
- `backend/app/api/routes/community_agent.py`

特征：

- 不自己验证 JWT
- 不自己查用户
- 把 token 交给 Supabase
- 数据可见性依赖 `auth.uid()`

#### B. 只为读取 `sub`，本地 decode JWT payload，不验签

见：

- `backend/app/api/routes/upload.py`
- `backend/app/api/routes/arxiv.py`
- `backend/app/api/routes/translate.py`
- `backend/app/api/routes/papers.py`

这些代码只是 base64 decode JWT payload 取 `sub` 作为 `user_id`，不做签名校验。  
当前它们主要用于：

- 给任务附加 `user_id`
- 在社区列表/detail 场景给 viewer 传 user_id
- 做 quota / task ownership 相关逻辑

迁移后，这部分不能继续沿用“只 decode 不验签”的方式，必须切换为正式的服务端鉴权中间件。

### 5.4 管理员鉴权现状

`backend/app/core/auth.py::require_admin_request()` 允许两种 admin 入口：

1. Bearer token 直接等于 `SUPABASE_SERVICE_ROLE_KEY`
2. Bearer token 是 Supabase user JWT，且 `auth.get_user(token)` 返回的 metadata 中包含：
   - `admin`
   - `service_role`
   - `supabase_admin`

但 live project 实测：

- `auth.users.raw_app_meta_data` 中带 role/roles 的用户数：0
- `auth.users.raw_user_meta_data` 中带 role/roles 的用户数：0
- `public.user_roles` 当前也为 0 行

这意味着当前“用户 JWT + metadata 角色”这条 admin 路径基本没有真实数据支撑。  
同时，数据库 RLS 的 admin 判断又是走 `public.user_roles`，不是走 Auth metadata。

这是一个重要的权限模型分裂点：

- API admin guard 看 Auth metadata
- DB RLS admin helper 看 `public.user_roles`

迁移时必须统一成一套角色模型。

## 6. 线上业务表清单

下表以 live project 为准：

| 表 | 行数 | RLS | 主要用途 | 主要代码触点 |
| --- | ---: | --- | --- | --- |
| `public.user_settings` | 4 | 开启 | 用户偏好、默认语言、模型、API key 密文、格式设置 | `settings.py`, `translate.py`, frontend `useStore.ts` |
| `public.translation_tasks` | 16 | 开启 | 已登录用户的翻译任务快照与历史 | `history.py`, `translate.py`, `task_manager.py`, `main.py` |
| `public.papers` | 10 | 开启 | 社区论文主表 | `paper_service.py`, `papers.py`, `main.py` |
| `public.paper_assets` | 317 | 开启 | 论文关联资源：源包、PDF、HTML 预览 | `paper_service.py`, `main.py` |
| `public.paper_likes` | 0 | 开启 | 用户点赞关系 | `paper_service.py`, RLS/社区功能 |
| `public.paper_favorites` | 0 | 开启 | 用户收藏关系 | `paper_service.py`, RLS/社区功能 |
| `public.comments` | 0 | 开启 | 评论与楼中楼 | `paper_service.py`, `main.py` |
| `public.reports` | 0 | 开启 | 举报记录 | `main.py` |
| `public.moderation_actions` | 0 | 开启 | 管理动作审计 | `main.py` |
| `public.notifications` | 0 | 开启 | 站内通知 | 目前主要是 schema 预留 |
| `public.user_roles` | 0 | 开启 | 管理员/版主角色 | RLS helper `current_user_is_admin()` |
| `public.user_bans` | 0 | 开启 | 封禁信息 | RLS helper `current_user_is_banned()` |
| `public.community_agent_conversations` | 47 | 开启 | 社区聊天历史 | `community_agent_service.py`, `community_agent.py` |

### 6.1 `user_settings`

核心字段：

- `user_id uuid unique default auth.uid()`
- `default_source_language`
- `default_target_language`
- `translation_mode`
- `compile_strategy`
- `translation_model`
- `enable_verification`
- `generate_glossary`
- `use_author_api`
- `custom_base_url`
- `custom_api_key_encrypted`
- `default_formatting jsonb`
- `created_at`
- `updated_at`

观察：

- `enable_verification` 列仍在线上表中，但当前前后端主流程基本已停止使用，是遗留字段。
- 只有 `user_settings` 配了 `updated_at` 自动触发器。

### 6.2 `translation_tasks`

核心字段：

- `task_id unique`
- `user_id default auth.uid()`
- `source_type`
- `arxiv_id`
- `source_language`
- `target_language`
- `translation_mode`
- `compile_strategy`
- `translation_model`
- `enable_verification`
- `generate_glossary`
- `use_author_api`
- `custom_base_url`
- `custom_api_key_encrypted`
- `status`
- `progress`
- `stage`
- `message`
- `error`
- `source_path`
- `output_path`
- `storage_path`
- `config_hash`
- `formatting`
- `detail_code`
- `detail_params`

观察：

- 这是登录用户历史与运行快照的核心表。
- 当前系统仍保留“本地文件系统 + Supabase 状态表”的双轨设计。
- `storage_path` 在线上存在，但当前代码主要仍用本地 `source_path/output_path`，没有实际启用 Supabase Storage。
- `enable_verification` 同样是遗留列。

### 6.3 社区论文域表

#### `papers`

承载：

- 论文来源：`upload` / `arxiv`
- 标题、作者、分类、摘要
- 可见性、发布状态
- 翻译状态
- 社区状态：`official` / `user_fallback`
- 计数器：点赞/收藏/评论/浏览/下载
- 软引用：`trans_latest_task_id`, `community_selected_task_id`

注意：

- `trans_latest_task_id` 和 `community_selected_task_id` 只是 `text`，没有 FK 到 `translation_tasks`。
- 这是一个“软关联”，迁移到 MySQL 时需要决定是否改成真实外键。

#### `paper_assets`

资源类型：

- `source_archive`
- `translated_pdf`
- `preview_pdf`
- `preview_html`

存储后端枚举：

- `local_disk`
- `object_storage`

但当前代码实际主要把 `file_path` 当本地路径处理。

#### `paper_likes` / `paper_favorites` / `comments`

是典型的“用户与论文交互表”，都强依赖：

- `auth.users.id`
- `papers.id`
- `auth.uid()` 驱动的 RLS 自拥有关系

#### `reports` / `moderation_actions` / `notifications` / `user_roles` / `user_bans`

构成社区治理与权限体系：

- `reports`：用户举报
- `moderation_actions`：管理动作
- `notifications`：通知
- `user_roles`：`admin` / `moderator`
- `user_bans`：封禁信息

虽然当前数据量为 0，但 schema、RLS、helper function 都已经在线上生效。

### 6.4 `community_agent_conversations`

字段：

- `user_id default auth.uid()`
- `conversation_id`
- `title`
- `turns jsonb`
- `created_at`
- `updated_at`

当前社区 agent 的对话历史是直接存在这张表里，不是存在前端 LocalStorage，也不是存在单独的聊天服务。

## 7. 当前 RLS / 授权模型

### 7.1 用户设置与翻译历史

`user_settings` 与 `translation_tasks` 的 RLS 最简单：

- `Users can view own ...`
- `Users can insert own ...`
- `Users can update own ...`
- `translation_tasks` 额外还有 delete own

条件几乎都是：

- `auth.uid() = user_id`

这两张表的策略角色是 `{public}`，所以匿名/已登录都走同一 policy 集合，但只有 JWT 中有合法 `sub` 才能命中自己的数据。

### 7.2 社区公开读

`papers` / `comments` 对匿名用户开放只读：

- `papers_public_read_anon`
- `comments_public_read_anon`

条件：

- 论文必须 `visibility = 'public'`
- 且 `status <> 'removed'`
- 评论还要求评论本身 `status = 'visible'`

### 7.3 社区登录用户写

以下表的写操作都依赖：

- `auth.uid() = user_id` 或 `reported_by`
- 某些写操作还要求 `not current_user_is_banned()`

涉及：

- `paper_likes`
- `paper_favorites`
- `comments`
- `reports`
- `community_agent_conversations`
- `notifications`（只允许标记自己的已读）

### 7.4 社区管理员/版主

管理员/版主权限通过数据库 helper function 间接实现：

- `public.current_user_is_admin()`
- `public.current_user_is_banned()`

`current_user_is_admin()` 逻辑：

- 查 `public.user_roles`
- `role in ('admin', 'moderator')`

`current_user_is_banned()` 逻辑：

- 查 `public.user_bans`
- `expires_at is null or expires_at > now()`

这些 helper 被用于：

- `papers` 管理更新
- `comments` 管理读/更新
- `reports` 管理读/更新
- `moderation_actions` 管理全权限
- `user_roles` 管理增删改
- `user_bans` 管理全权限
- `paper_assets` 管理只读

### 7.5 自动 RLS 启用

线上还有一个额外的数据库行为：

- event trigger：`ensure_rls`
- 对应函数：`public.rls_auto_enable()`

作用：

- 对新建的 `public` 表自动执行 `ENABLE ROW LEVEL SECURITY`

这不是代码里显式调用的，而是数据库侧自动行为。  
迁移到 MySQL 后不会自动存在，需要在 schema review / migration review 中显式接管。

## 8. 当前函数、触发器、索引、Storage、扩展

### 8.1 当前线上 `public` 函数

live project 当前存在：

- `current_user_is_admin()`
- `current_user_is_banned()`
- `increment_paper_view_count(uuid)`
- `rls_auto_enable()`
- `update_updated_at_column()`

用途：

- 前两个负责社区 RLS helper
- `increment_paper_view_count()` 被 `paper_service.py` 调用
- `rls_auto_enable()` 由 event trigger `ensure_rls` 触发
- `update_updated_at_column()` 目前只给 `user_settings` 的 `updated_at` 触发器使用

### 8.2 当前线上不存在但代码会调用的函数

代码会调用：

- `increment_paper_download_count(uuid)`

仓库里也有 migration：

- `backend/migrations/20260318_add_increment_paper_download_count_fn.sql`

但 live project 当前不存在这个函数。  
因此当前下载计数逻辑实际上是：

- 尝试 RPC
- 失败后记录 warning
- 不阻断下载

这是一个明确的线上漂移点。

### 8.3 当前线上触发器

当前查到的业务触发器只有 1 个：

- `update_user_settings_updated_at`
  - 表：`user_settings`
  - 时机：`BEFORE UPDATE`
  - 函数：`update_updated_at_column()`

说明：

- 并不是所有带 `updated_at` 的表都使用数据库触发器
- `papers`、`comments` 等大量表更依赖应用层手动写 `updated_at`

### 8.4 当前线上索引

重要索引包括：

- `translation_tasks_task_id_key`
- `translation_tasks_user_created_at_idx`
- `translation_tasks_user_status_idx`
- `idx_translation_tasks_config_hash`
- `user_settings_user_id_key`
- `papers_arxiv_id_unique_idx`
- `papers_visibility_status_created_at_idx`
- `papers_trans_status_created_at_idx`
- `papers_community_status_created_at_idx`
- `community_agent_conversations_user_updated_idx`

其中 Supabase Advisor 报告以下索引当前未被使用：

- `papers_official_published_at_idx`
- `translation_tasks_user_status_idx`
- `reports_status_created_at_idx`

### 8.5 Storage

当前 storage 状态：

- bucket：`product`
- `public = false`
- `storage.objects = 0`

代码侧观察：

- 没有前后端直接调用 `supabase.storage.from(...)`
- `paper_assets.file_path` 当前主要保存本地路径
- `translation_tasks.storage_path` 只是预留字段

结论：当前项目并没有真正依赖 Supabase Storage 作为运行主路径。

### 8.6 扩展

项目中安装了很多平台级扩展，但从代码和 schema 依赖来看，真正与当前业务明显相关的主要是：

- `pgcrypto`：用于 `gen_random_uuid()`
- `uuid-ossp`
- `pg_stat_statements`
- `supabase_vault`
- `pg_graphql`

此外还有大量 Supabase 平台默认可选扩展，但当前业务代码没有直接依赖。

### 8.7 Edge Functions

当前没有任何 Supabase Edge Function。

## 9. 代码与表的映射关系

### 9.1 `user_settings`

使用位置：

- `backend/app/api/routes/settings.py`
  - 读取当前用户设置
  - 更新当前用户设置
- `backend/app/api/routes/translate.py`
  - 后端用 admin client 读取用户加密 API key 与自定义 base URL
- `frontend/src/store/useStore.ts`
  - 登录后加载设置
  - 初始化翻译默认配置

迁移意义：

- 这张表既是用户偏好表，也是“用户私有 LLM 配置”表
- 迁移时需要考虑敏感字段加密方案

### 9.2 `translation_tasks`

使用位置：

- `backend/app/services/task_manager.py`
  - 首次持久化
  - 节流更新
  - 重试持久化
  - 重启恢复
  - 失败任务删除
- `backend/app/api/routes/history.py`
  - 用户历史列表/详情/删除
- `backend/app/api/routes/translate.py`
  - 查重复配置、持久化 `config_hash`
- `backend/app/main.py`
  - 启动时标记中断任务为失败
  - 清理孤儿目录/无效任务

迁移意义：

- 这是最核心的“运行态落库表”
- 迁移不能只迁数据，还要迁整套运行时语义

### 9.3 社区表

使用位置主要集中在：

- `backend/app/services/paper_service.py`
- `backend/app/api/routes/papers.py`
- `backend/app/main.py`

特点：

- 大部分社区读写都通过 admin client 完成
- 对外公开访问由应用层自己做“只返回 public/published”，并不依赖前端直接访问 Supabase

迁移意义：

- 社区域迁移本质上是正常数据库迁移
- 真正复杂的是把现在数据库侧 helper/RLS 迁到应用层权限系统

### 9.4 `community_agent_conversations`

使用位置：

- `backend/app/services/community_agent_service.py`
- `backend/app/api/routes/community_agent.py`

特点：

- 读写都走用户态 token + RLS
- 每个用户看不到别人的对话

迁移意义：

- 需要自建“按 user_id 隔离”的聊天会话表与接口层权限

### 9.5 content pool

注意：当前 `community_content_pool_service.py` 是内存态服务，不是数据库服务。

- readiness snapshot：内存
- event/job log：内存
- 当前 API 可以访问，但不会落 Supabase 表

仓库里虽然有：

- `community_content_pool_candidates`
- `community_content_pool_jobs`
- `community_content_pool_job_events`

但 live project 里这三张表不存在。  
所以它们属于“已设计/已写 migration，但当前线上未投入使用”。

## 10. 当前线上与仓库的差异

### 10.1 线上有、仓库当前 migration 目录里看不全

最典型的是：

- `user_settings`
- `translation_tasks`

仓库 `backend/migrations/` 里没有它们的完整建表 SQL，但 live project 的 migration 历史显示它们来自更早的 migration：

- `create_user_settings_and_translation_tasks`
- `add_user_id_default_trigger`
- `add_storage_path_to_translation_tasks`
- `add_delete_policy_for_translation_tasks`
- `add_folder_upload_source_type`
- `add_config_hash_to_translation_tasks`
- `add_default_formatting_to_user_settings`
- `add_task_detail_metadata`

这意味着：

- 当前仓库并不能单靠本地 SQL 完整重建线上状态
- 做迁移计划时必须以 live schema 为主，而不是只看仓库 SQL

### 10.2 仓库有、线上没应用

目前明确看到：

- `increment_paper_download_count()` 函数：仓库有，线上没有
- `community_content_pool_*` 三张表：仓库有，线上没有

### 10.3 权限模型分裂

存在两套角色入口：

- API admin guard：看 Auth metadata
- DB RLS admin helper：看 `public.user_roles`

live 数据中两边都没有 admin 用户记录。  
迁移时需要统一角色来源，不然会继续产生“接口说你不是 admin，数据库也没有 admin”的双重不一致。

## 11. 迁移到 MySQL 时需要补做的能力清单

建议把迁移拆成两层：基础能力迁移 + 业务表迁移。

### 11.1 基础能力迁移

必须自建：

- 用户主表
- 密码哈希与密码校验
- 注册/登录接口
- 邮箱确认或 OTP 验证机制
- 会话表 / refresh token 表
- JWT 签发、续期、失效
- 服务端 JWT 校验中间件
- 角色表 / 封禁表
- 统一的管理员判定逻辑

### 11.2 原 RLS 能力替换

需要在应用层显式补回：

- `user_settings.user_id = current_user_id`
- `translation_tasks.user_id = current_user_id`
- `community_agent_conversations.user_id = current_user_id`
- 评论/点赞/收藏/举报只能操作自己
- 管理员/版主可额外查看/更新社区内容
- 被封禁用户禁止执行某些写操作

### 11.3 业务表迁移

需要迁移的核心业务表：

- `user_settings`
- `translation_tasks`
- `papers`
- `paper_assets`
- `paper_likes`
- `paper_favorites`
- `comments`
- `reports`
- `moderation_actions`
- `notifications`
- `user_roles`
- `user_bans`
- `community_agent_conversations`

是否迁移：

- `auth.users`：是，必须迁移到自建用户表
- `auth.identities` / `auth.sessions` / `auth.refresh_tokens`：如果切换为新认证体系，需要做数据承接或平滑失效方案
- `storage`：当前可不作为首要迁移目标
- `community_content_pool_*`：当前线上未用，可后置

### 11.4 兼容性建议

迁移时建议优先保留这些语义：

- 用户主键继续用 UUID
- `task_id` 继续保留唯一约束
- 软关联字段是否升级为 FK，需要单独设计
- `formatting` / `default_formatting` 继续保留 JSON
- `custom_api_key_encrypted` 继续加密存储

## 12. 迁移风险与特别提醒

### 12.1 不能只迁表结构

当前 Supabase 不只是“数据库”：

- 它还承接了 Auth
- Session
- JWT
- RLS
- helper function
- event trigger
- service-role 绕过权限

如果只把表搬到 MySQL，而不重建这些语义，系统会立刻出现权限缺失和行为回退。

### 12.2 当前代码里存在“只 decode JWT，不验签”的路径

这些路径迁移后必须统一替换成：

- 先验签
- 再拿 user_id
- 再做业务逻辑

否则会留下安全风险。

### 12.3 Admin 设计必须先统一

在开始迁移前，建议先定一条统一原则：

- 管理员/版主角色到底存在用户表 metadata，还是存在单独 `user_roles` 表？

当前系统两边都沾了一点，但没有真正统一。

### 12.4 以 live schema 为准

做迁移计划时，必须优先以 live project 当前状态为准，因为：

- 线上 `user_settings` / `translation_tasks` 比仓库 SQL 更完整
- 仓库里还有未应用对象
- 线上还有 event trigger 和函数行为

## 13. 可直接作为迁移计划输入的结论

如果下一步要基于本报告生成迁移计划，建议直接围绕以下 6 个主题展开：

1. Supabase Auth -> 自建 Auth 的替换方案
2. RLS -> 应用层权限中间件/Repository 过滤的替换方案
3. `user_settings` + `translation_tasks` 的迁移与运行态兼容
4. 社区域表 (`papers` 及相关表) 的迁移与权限重建
5. 启动清理、任务恢复、计数函数等系统行为迁移
6. 线上 schema 漂移治理：以 live schema 回写正式 migration 基线

## 14. 附录：当前 live project 的非业务对象结论

- Publishable/Client keys：
  - legacy `anon` key：启用
  - publishable key：启用
- Edge Functions：0
- Storage bucket：1 个（`product`），对象 0
- 安全 Advisor：
  - `public.update_updated_at_column` 的 `search_path` 可变，提示安全告警
  - Supabase Auth 的 leaked password protection 未开启

---

如果你要继续下一步，我建议直接基于这份文档生成两份后续材料：

1. `supabase_to_mysql_migration_plan.md`
2. `custom_auth_and_authorization_design.md`

第一份聚焦数据与落地顺序，第二份聚焦登录、JWT、权限与管理员模型。

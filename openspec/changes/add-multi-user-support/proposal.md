# 多用户支持功能增强提案

## 变更概述

为 LaTeXTrans 系统新增完整的多用户支持能力，包括用户认证、用户级翻译历史、系统设置持久化和用户资料页面。

## 背景

当前系统状态：
- **临时访问功能已完善** - 新建翻译页面支持 arXiv 论文 ID 访问、拖拽上传（zip/rar/tar.gz），高级配置完整可用
- 无用户认证机制
- 任务状态存储在内存中，服务器重启后丢失
- 所有用户共享临时任务，无法保存历史
- 系统设置页面、历史记录页面为占位页面
- 用户每次新建翻译都需重新配置

## 目标

基于 Supabase 实现真实可用的多用户能力，同时保持访客模式可用：

1. **用户注册与登录** - 使用 Supabase Auth 邮箱密码方式
2. **访客模式** - 未登录用户可使用临时翻译（不持久化）
3. **翻译历史** - 登录用户任务持久化存储，支持预览和下载历史译文
4. **系统设置** - 登录用户可保存个人默认配置，自动应用于新建翻译
5. **用户资料** - 显示登录邮箱、支持登出和切换账号

> [!NOTE]
> **临时访问功能**（含拖拽上传、高级配置、进度显示、双向对比、术语表显示等）已在 `add-advanced-config-temp-user` 中实现，本变更直接复用。

> [!NOTE]
> **术语库管理功能** 将在后续 RAG 相关变更中实现，本变更不涉及。

## 核心功能设计

### 访客模式 vs 登录用户

| 功能 | 访客用户 | 登录用户 |
|------|----------|----------|
| 新建翻译（ArXiv / 拖拽上传） | ✅ | ✅ |
| 高级配置调整 | ✅ | ✅ |
| 翻译执行与预览 | ✅ | ✅ |
| 下载 PDF / 源文件 | ✅ | ✅ |
| 翻译历史记录 | ❌ | ✅ |
| 系统设置保存 | ❌ | ✅ |
| 配置自动填充 | ❌ | ✅ |

> [!IMPORTANT]
> **核心概念**：访客任务 = 临时 task（内存存储），登录用户任务 = 持久 task（Supabase 存储）

### 系统设置配置项

登录用户可保存以下个人默认配置：

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| 源语言 | 枚举 | en | 源文档语言 |
| 目标语言 | 枚举 | zh | 翻译目标语言 |
| 翻译模式 | 枚举 | full | `full`=全文翻译, `quick_scan`=文献快速筛查（仅摘要+结论） |
| 编译策略 | 枚举 | auto | `auto`=自动检测, `pdflatex`, `xelatex`, `lualatex` |
| 翻译模型 | 字符串 | - | 用户选择的翻译模型 |
| 启用验证代理 | 布尔 | true | 是否启用翻译验证 |
| 生成术语表 | 布尔 | true | 是否生成术语表 |
| 使用作者默认 API | 布尔 | true | 是否使用系统内置 API |
| 自定义 Base URL | 字符串 | null | 中转 API 主网站（如 `www.example.com`，系统自动追加 `/v1/chat/...`） |
| 自定义 API Key | 字符串 | null | 用户自己的 API Key |

### 历史记录存储内容

每条翻译任务记录包含：

| 字段 | 说明 |
|------|------|
| arXiv 论文 ID | 主要识别标识（用于源 PDF 展示和任务识别） |
| 配置快照 | 该次翻译使用的所有配置项 |
| 输出文件路径 | 系统内部使用，用于提供预览和下载 |
| 任务状态 | pending / running / completed / failed |
| 创建时间 | 任务创建时间戳 |
| 完成时间 | 任务完成时间戳 |

> [!IMPORTANT]
> PDF 文件存储在后端硬盘（`data/outputs/{task_id}/`），不存入 Supabase 数据库。Supabase 仅存储元数据和路径引用。

### 用户资料页面

简单的账户信息展示页面：
- 显示当前登录账户邮箱（不可修改）
- 登出按钮
- 切换到其他账号（先登出再登录）

## Supabase 使用范围

| 组件 | 用途 |
|------|------|
| Supabase Auth | 用户注册、登录、JWT 验证 |
| Supabase Postgres | 用户设置、任务元数据存储 |

## 数据库表设计

### 表 1: `user_settings` - 用户设置

```sql
CREATE TABLE public.user_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    -- 语言设置
    default_source_language TEXT NOT NULL DEFAULT 'en',
    default_target_language TEXT NOT NULL DEFAULT 'zh',
    -- 翻译设置
    translation_mode TEXT NOT NULL DEFAULT 'full' CHECK (translation_mode IN ('full', 'quick_scan')),
    compile_strategy TEXT NOT NULL DEFAULT 'auto' CHECK (compile_strategy IN ('auto', 'pdflatex', 'xelatex', 'lualatex')),
    translation_model TEXT,
    enable_verification BOOLEAN NOT NULL DEFAULT true,
    generate_glossary BOOLEAN NOT NULL DEFAULT true,
    -- API 设置
    use_author_api BOOLEAN NOT NULL DEFAULT true,
    custom_base_url TEXT,
    custom_api_key_encrypted TEXT,  -- AES-256 加密存储
    -- 时间戳
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(user_id)
);
```

### 表 2: `translation_tasks` - 翻译任务

```sql
CREATE TABLE public.translation_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id TEXT NOT NULL UNIQUE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    -- 任务来源
    source_type TEXT NOT NULL CHECK (source_type IN ('upload', 'arxiv')),
    arxiv_id TEXT,
    -- 配置快照
    source_language TEXT NOT NULL,
    target_language TEXT NOT NULL,
    translation_mode TEXT NOT NULL DEFAULT 'full',
    compile_strategy TEXT NOT NULL DEFAULT 'auto',
    translation_model TEXT,
    enable_verification BOOLEAN NOT NULL DEFAULT true,
    generate_glossary BOOLEAN NOT NULL DEFAULT true,
    use_author_api BOOLEAN NOT NULL DEFAULT true,
    custom_base_url TEXT,
    custom_api_key TEXT,
    -- 任务状态
    status TEXT NOT NULL DEFAULT 'pending',
    progress INTEGER NOT NULL DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
    stage TEXT NOT NULL DEFAULT 'idle',
    message TEXT,
    error TEXT,
    -- 文件路径（系统内部使用）
    source_path TEXT,
    output_path TEXT,
    -- 时间戳
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);
```

### Row Level Security (RLS) 策略

```sql
-- 启用 RLS
ALTER TABLE public.user_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.translation_tasks ENABLE ROW LEVEL SECURITY;

-- user_settings: 用户只能访问自己的设置
CREATE POLICY "Users can view own settings" ON public.user_settings
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own settings" ON public.user_settings
    FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own settings" ON public.user_settings
    FOR UPDATE USING (auth.uid() = user_id);

-- translation_tasks: 用户只能访问自己的任务
CREATE POLICY "Users can view own tasks" ON public.translation_tasks
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own tasks" ON public.translation_tasks
    FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own tasks" ON public.translation_tasks
    FOR UPDATE USING (auth.uid() = user_id);
```

## 安全设计

### API Key 加密存储

用户自定义 API Key 使用 AES-256 加密存储于数据库，后端使用 `ENCRYPTION_KEY` 环境变量进行加解密。

### 邮箱验证

新用户注册后需通过邮箱验证才能正常登录。需配置 Supabase Email Provider（推荐 Resend 或 SMTP）。

### 会话管理

- JWT Access Token: 1 小时过期
- Refresh Token: 7 天过期
- 支持自动刷新 Token

## 配置继承模型

### 三层配置架构

```
UserConfig (用户默认配置 - 来自系统设置)
    ↓
TaskConfig (单次任务可覆盖 - 新建翻译时调整)
    ↓
RuntimeConfig (最终执行配置)
```

### 行为规则

1. **新建翻译时**：
   - 已登录用户：从系统设置读取 UserConfig，自动填充到高级配置 UI
   - 未登录用户：使用系统默认值
2. **单次任务修改**：
   - 允许临时修改配置 (TaskConfig)
   - 不影响用户全局配置 (UserConfig)
3. **执行时合并**：
   - `RuntimeConfig = merge(UserConfig, TaskConfig)`

## 验证计划

### 自动化测试
- 用户注册、登录、登出流程
- 系统设置 CRUD 操作
- 翻译任务持久化和历史查询
- RLS 策略验证（用户隔离）

### 手动验证
- 访客模式：未登录创建翻译 → 成功执行 → 刷新页面后任务丢失
- 登录模式：创建翻译 → 刷新页面/服务器重启 → 历史记录保留
- 配置继承：设置默认配置 → 新建翻译时自动填充

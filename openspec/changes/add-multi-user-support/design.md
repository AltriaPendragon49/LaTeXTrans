# 架构设计文档

## 设计目标

1. **最小侵入性** - 不破坏现有临时访问翻译流程
2. **渐进式迁移** - 保留内存任务管理作为实时缓存
3. **清晰分层** - 认证、任务元数据、文件存储各司其职
4. **配置继承** - 用户设置自动应用于新建翻译

## 系统分层

```
┌─────────────────────────────────────────────────────────────┐
│                      前端 (React + Vite)                     │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐ │
│  │登录页面  │  │新建翻译  │  │历史记录  │  │系统设置      │ │
│  │/login    │  │/         │  │/history  │  │/settings     │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘ │
│       │             │             │               │         │
│       │     ┌───────┴───────┐     │               │         │
│       │     │用户资料       │     │               │         │
│       │     │/profile       │     │               │         │
│       │     └───────────────┘     │               │         │
│       │             │             │               │         │
│  ┌────┴─────────────┴─────────────┴───────────────┴───────┐ │
│  │               Supabase Client (Auth + API)              │ │
│  │               + Axios (Backend API)                     │ │
│  └─────────────────────────────────────────────────────────┘ │
└────────────────────────────────┬────────────────────────────┘
                                 │ HTTP + JWT
                                 ▼
┌─────────────────────────────────────────────────────────────┐
│                    后端 (FastAPI)                            │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐ │
│  │         可选 JWT 验证中间件 (支持访客模式)               │ │
│  └────────────────────────────┬────────────────────────────┘ │
│                               │ user_id (可选)               │
│  ┌────────────┬───────────────┼───────────────┬────────────┐ │
│  │ /api/arxiv │ /api/upload   │ /api/task     │/api/settings│ │
│  │ /api/trans │ /api/download │ /api/history  │/api/profile │ │
│  └─────┬──────┴───────┬───────┴───────┬───────┴──────┬─────┘ │
│        │              │               │              │        │
│  ┌─────┴──────────────┴───────────────┴──────────────┴─────┐ │
│  │                    TaskManager (重构)                    │ │
│  │  ┌─────────────────┐    ┌──────────────────────┐        │ │
│  │  │ 内存缓存层       │◄──►│ Supabase 持久化层     │        │ │
│  │  │ (所有任务)       │    │ (仅登录用户任务)      │        │ │
│  │  └─────────────────┘    └──────────────────────┘        │ │
│  └─────────────────────────────────────────────────────────┘ │
│                               │                               │
│  ┌────────────────────────────┴────────────────────────────┐ │
│  │                 本地文件系统 (PDF 存储)                  │ │
│  │        data/uploads/{task_id}/  (源文件)                 │ │
│  │        data/outputs/{task_id}/  (翻译结果 PDF)           │ │
│  └─────────────────────────────────────────────────────────┘ │
└────────────────────────────────┬────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────┐
│                    Supabase 云服务                           │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐    ┌─────────────────────────────────────┐ │
│  │ Auth         │    │ PostgreSQL                          │ │
│  │ (用户认证)   │    │  ├── auth.users (内置)              │ │
│  │              │    │  ├── user_settings                  │ │
│  │              │    │  └── translation_tasks              │ │
│  └──────────────┘    └─────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 关键设计决策

### 1. 双层任务管理

**问题**: 如何在保持实时状态更新的同时实现持久化？

**方案**: TaskManager 采用双层架构

```python
class TaskManager:
    def __init__(self):
        self._cache: Dict[str, TaskData] = {}  # 内存缓存（所有任务）
        self._supabase = get_supabase_client()  # 持久化层

    def create_task(self, user_id: Optional[str], config: TaskConfig) -> str:
        task_id = generate_task_id()

        # 1. 创建内存缓存（所有任务都需要）
        self._cache[task_id] = TaskData(...)

        # 2. 仅登录用户持久化到 Supabase
        if user_id:
            self._supabase.table("translation_tasks").insert({
                "task_id": task_id,
                "user_id": user_id,
                "arxiv_id": config.arxiv_id,
                "source_language": config.source_language,
                "target_language": config.target_language,
                "translation_mode": config.translation_mode,
                "compile_strategy": config.compile_strategy,
                # ... 其他配置快照
            }).execute()

        return task_id

    def update_task(self, task_id: str, user_id: Optional[str], **kwargs):
        # 1. 更新内存缓存（实时）
        self._cache[task_id].update(**kwargs)

        # 2. 仅登录用户异步更新 Supabase
        if user_id:
            asyncio.create_task(self._persist_to_supabase(task_id, kwargs))
```

**优势**:
- 访客任务：仅内存存储，关闭即失效
- 登录用户任务：内存 + Supabase，持久保存
- 实时状态更新不阻塞

### 2. 可选 JWT 验证

**问题**: 如何支持访客模式同时验证登录用户？

**方案**: 可选 JWT 验证依赖注入

```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from typing import Optional

security = HTTPBearer(auto_error=False)  # 不自动报错

async def get_optional_user(
    token: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[str]:
    """返回 user_id 或 None（访客模式）"""
    if token is None:
        return None  # 访客模式

    try:
        user = supabase.auth.get_user(token.credentials)
        return user.user.id
    except Exception:
        return None  # Token 无效，降级为访客
```

**使用方式**:

```python
@router.post("/translate/{task_id}")
async def start_translation(
    task_id: str,
    user_id: Optional[str] = Depends(get_optional_user)
):
    # user_id 可能为 None（访客）或有效 UUID（登录用户）
    pass
```

### 3. 配置继承流程

**问题**: 如何实现用户设置自动填充到新建翻译？

**方案**: 三层配置合并

```
┌─────────────────────────────────────────────────────────────┐
│ 1. 系统默认值 (SystemDefaults)                              │
│    - source_language: "en"                                  │
│    - target_language: "zh"                                  │
│    - translation_mode: "full"                               │
│    - compile_strategy: "auto"                               │
│    - enable_verification: true                              │
│    - generate_glossary: true                                │
│    - use_author_api: true                                   │
└─────────────────────────┬───────────────────────────────────┘
                          ↓ 覆盖
┌─────────────────────────────────────────────────────────────┐
│ 2. 用户设置 (UserConfig from /api/settings)                │
│    - 登录用户从 Supabase 读取                               │
│    - 访客用户跳过此层                                       │
└─────────────────────────┬───────────────────────────────────┘
                          ↓ 覆盖
┌─────────────────────────────────────────────────────────────┐
│ 3. 任务配置 (TaskConfig from 高级配置 UI)                   │
│    - 用户在新建翻译时临时修改的配置                          │
│    - 不影响 UserConfig                                      │
└─────────────────────────┬───────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. 运行时配置 (RuntimeConfig)                               │
│    - 最终用于翻译执行的配置                                  │
│    - 同时保存到 translation_tasks 表作为配置快照             │
└─────────────────────────────────────────────────────────────┘
```

**前端实现**:

```typescript
// 新建翻译页面加载时
async function loadDefaultConfig() {
  const user = await supabase.auth.getUser();

  if (user) {
    // 登录用户：从系统设置读取
    const settings = await api.getSettings();
    setConfig({
      sourceLanguage: settings.default_source_language,
      targetLanguage: settings.default_target_language,
      translationMode: settings.translation_mode,
      compileStrategy: settings.compile_strategy,
      // ...
    });
  } else {
    // 访客用户：使用系统默认值
    setConfig(SYSTEM_DEFAULTS);
  }
}
```

### 4. PDF 存储策略

**问题**: PDF 文件如何存储和访问？

**方案**: 本地存储 + 路径引用

```
存储位置:
  data/outputs/{task_id}/
    ├── translated.pdf    # 译文 PDF
    ├── source.pdf        # 源 PDF（如果有）
    └── glossary.json     # 术语表（如果生成）

Supabase 存储:
  translation_tasks.output_path = "data/outputs/{task_id}"

访问流程:
  1. 前端请求: GET /api/download/{task_id}/translated.pdf
  2. 后端验证: 检查 task.user_id == current_user_id
  3. 从本地读取: 根据 task.output_path 读取文件
  4. 返回文件流
```

**优势**:
- 不占用 Supabase 存储空间
- 大文件传输更高效
- 现有存储结构不变

### 5. arXiv ID 作为主要标识

**问题**: 历史记录如何展示任务？

**方案**: 以 arXiv ID 为主要展示标识

```
历史记录列表展示:
  ┌─────────────────────────────────────────────────────────┐
  │ 📄 2301.12345                                           │
  │    翻译模式: 全文翻译 | 状态: ✅ 完成                    │
  │    创建时间: 2026-02-07 12:00                           │
  │    [查看详情] [下载 PDF]                                 │
  ├─────────────────────────────────────────────────────────┤
  │ 📄 2402.67890                                           │
  │    翻译模式: 快速筛查 | 状态: ⏳ 进行中                  │
  │    创建时间: 2026-02-07 11:30                           │
  ├─────────────────────────────────────────────────────────┤
  │ 📁 上传文件                                             │
  │    翻译模式: 全文翻译 | 状态: ✅ 完成                    │
  │    创建时间: 2026-02-07 10:00                           │
  │    [查看详情] [下载 PDF]                                 │
  └─────────────────────────────────────────────────────────┘
```

## 文件变更概览

### 后端新增文件

| 文件 | 用途 |
|------|------|
| `app/core/supabase_client.py` | Supabase 客户端初始化 |
| `app/core/auth.py` | 可选 JWT 验证依赖注入 |
| `app/api/routes/settings.py` | 用户设置 CRUD |
| `app/api/routes/history.py` | 翻译历史查询 |
| `app/api/routes/profile.py` | 用户资料（简单） |

### 后端修改文件

| 文件 | 修改内容 |
|------|----------|
| `app/services/task_manager.py` | 添加 Supabase 持久化层、支持配置快照 |
| `app/api/routes/upload.py` | 注入可选 user_id |
| `app/api/routes/arxiv.py` | 注入可选 user_id |
| `app/api/routes/translate.py` | 注入可选 user_id，保存配置快照 |
| `app/api/routes/task.py` | 用户隔离查询 |
| `app/api/routes/download.py` | 验证用户权限 |
| `app/main.py` | 注册新路由 |
| `app/core/config.py` | 添加 Supabase 配置 |
| `requirements.txt` | 添加 supabase 依赖 |

### 前端新增文件

| 文件 | 用途 |
|------|------|
| `src/lib/supabase.ts` | Supabase 客户端 |
| `src/contexts/AuthContext.tsx` | 认证上下文 |
| `src/hooks/useAuth.ts` | 认证 hook |
| `src/pages/Login.tsx` | 登录/注册页面 |
| `src/pages/History.tsx` | 历史记录页面 |
| `src/pages/Settings.tsx` | 系统设置页面 |
| `src/pages/Profile.tsx` | 用户资料页面（简单） |

### 前端修改文件

| 文件 | 修改内容 |
|------|----------|
| `src/App.tsx` | 添加路由和 AuthProvider |
| `src/lib/api.ts` | 添加认证头（可选）、新增 API 函数 |
| `src/components/app-sidebar.tsx` | 用户信息展示、登录/登出按钮 |
| `src/pages/Dashboard.tsx` | 从用户设置加载默认配置 |

## 安全考虑

### 1. RLS 策略
- 所有数据库表启用 RLS
- 使用 `(SELECT auth.uid())` 包装避免每行调用
- 确保用户只能访问自己的数据

### 2. JWT 验证
- 登录用户请求必须携带有效 JWT
- Access Token: 1 小时过期
- Refresh Token: 7 天过期
- 支持自动续期

### 3. 文件权限
- 下载接口验证 task 归属当前用户
- 历史记录只返回当前用户任务

### 4. API Key 加密存储

```python
# 使用 cryptography 库实现 AES-256 加密
from cryptography.fernet import Fernet

class APIKeyEncryption:
    def __init__(self, encryption_key: str):
        # ENCRYPTION_KEY 环境变量，32字节 Base64 编码
        self.fernet = Fernet(encryption_key.encode())
    
    def encrypt(self, api_key: str) -> str:
        return self.fernet.encrypt(api_key.encode()).decode()
    
    def decrypt(self, encrypted_key: str) -> str:
        return self.fernet.decrypt(encrypted_key.encode()).decode()
```

### 5. 邮箱验证流程

```
注册请求 → Supabase Auth → 发送验证邮件 → 用户点击链接 → 验证完成 → 可登录
```

需配置 Supabase Email Provider:
- 推荐: Resend (免费额度 3000/月)
- 备选: 自定义 SMTP

### 6. 敏感信息管理
- Supabase 配置通过环境变量管理
- `ENCRYPTION_KEY` 用于 API Key 加解密
- Service Role Key 仅用于后端

## 性能考虑

1. **任务轮询** - 继续使用内存缓存，不增加数据库查询
2. **批量查询** - 历史记录支持分页，避免一次加载过多
3. **连接池** - Supabase client 使用单例，复用连接
4. **懒加载** - 用户设置首次访问时创建默认值
5. **索引优化** - 遵循 Supabase Best Practices 为查询列添加索引

---

## 认证架构重构 (2026-02-08)

### 问题背景

原设计使用 `supabase.auth.get_user(token)` 在后端验证 JWT，但遇到持续的 `Invalid API key` 错误。
经排查发现：
1. Supabase SDK 的 `auth.get_user()` 对 service_role_key 的使用有兼容性问题
2. gotrue/httpx 依赖版本冲突导致 `proxy` 参数错误

### 设计决策：纯 RLS 模式

采用 **Supabase 官方最终推荐形态**：

```
原架构 (已废弃):
前端 access_token → 后端 auth.get_user(token) 验证 → 提取 user_id → admin client 操作

新架构 (纯 RLS):
前端 access_token → 后端透传给 user client → RLS 使用 auth.uid() 自动控制权限
```

### 核心原则

1. **后端不验证 token** - 删除所有 `auth.get_user()` 调用
2. **后端不解析 user** - 不需要获取 user_id
3. **RLS 控制一切** - `auth.uid() = user_id` 策略自动过滤数据
4. **token 透传** - access_token 传递给 Supabase client，SDK 自动处理认证

### 关键实现

#### auth.py
```python
def create_supabase_client_with_token(access_token: str) -> Client:
    """使用 anon_key + access_token 创建用户上下文客户端"""
    client = create_client(supabase_url, supabase_anon_key)
    client.auth.set_session(access_token, "")
    return client  # RLS 自动生效
```

#### settings.py / history.py
```python
@router.get("/settings")
async def get_user_settings(
    supabase: Optional[Client] = Depends(get_supabase_client_from_request)
):
    # 不需要 user_id，RLS 自动过滤
    result = supabase.table("user_settings").select("*").execute()
```

### 数据库迁移

```sql
-- INSERT 时自动填充 user_id
ALTER TABLE user_settings ALTER COLUMN user_id SET DEFAULT auth.uid();
ALTER TABLE translation_tasks ALTER COLUMN user_id SET DEFAULT auth.uid();
```

### 依赖变更

```
# requirements.txt
supabase>=2.0.0
httpx>=0.25.0
```

移除固定版本锁定，让 pip 自动解析兼容的 supabase/httpx 版本组合。

### 文件变更

| 文件 | 变更 |
|------|------|
| `app/core/auth.py` | 重构：删除 get_user()，改为 token 透传模式 |
| `app/core/config.py` | 添加 supabase_anon_key |
| `app/core/supabase_client.py` | 简化：保留 admin_client 用于系统操作 |
| `app/api/routes/settings.py` | 重构：使用纯 RLS 模式 |
| `app/api/routes/history.py` | 重构：使用纯 RLS 模式 |
| `backend/.env` | 添加 SUPABASE_ANON_KEY |
| `backend/start.bat` | 更新环境变量检查 |
| `requirements.txt` | 更新依赖版本 |

---

## API Key 解密传递修复 (2026-02-09)

### 问题背景

用户在系统设置 (`/settings`) 中配置了自定义 API Key 后，翻译时未正确使用该 API Key，而是错误使用了前端高级配置中传递的值（或回退到作者 API）。

日志显示：
```
WARNING - Supabase admin client not available
No API key found in system settings for user xxx
Using API key from request (frontend advanced config)
```

### 根因分析

1. **Supabase Admin Client 未初始化**：`.env` 文件缺少 `SUPABASE_SERVICE_ROLE_KEY` 变量，导致 `get_supabase_admin_client()` 返回 `None`
2. **API 优先级逻辑缺陷**：原有的 `get_user_api_config()` 包含冗余的 `use_author_api` 检查
3. **解密流程未启用**：系统设置中的 API Key 存储为加密格式，但后端未正确调用解密

### 解决方案

#### 1. 环境变量配置

在 `backend/.env` 中添加 Service Role Key：
```
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIs...
```

#### 2. API 优先级重构

在 `translate.py` 中重构 `build_llm_config()` 函数，建立清晰的 API Key 优先级：

```python
# Priority 1: 作者 API (use_author_api=True)
if advanced_config.use_author_api:
    return settings.get_llm_config()

# Priority 2: 用户系统设置 (从 Supabase 解密获取)
if user_id:
    user_api_config = get_user_api_config(user_id)
    if user_api_config.get("api_key"):
        return {"api_key": user_api_config["api_key"], ...}

# Priority 3: 前端高级配置 (临时覆盖)
if advanced_config.custom_api_key:
    return {"api_key": advanced_config.custom_api_key, ...}

# Fallback: 作者 API
return settings.get_llm_config()
```

#### 3. 解密逻辑增强

在 `encryption.py` 中增强 `decrypt_api_key()` 函数的日志输出：

```python
def decrypt_api_key(encrypted_key: str) -> Optional[str]:
    if not encrypted_key:
        logger.warning("decrypt_api_key: encrypted_key is empty")
        return None
    
    fernet = _get_fernet()
    if fernet is None:
        logger.info("Fernet not configured, returning key as plaintext")
        return encrypted_key
    
    try:
        decrypted = fernet.decrypt(encrypted_key.encode()).decode()
        logger.info(f"Successfully decrypted API key (prefix={decrypted[:4]}...)")
        return decrypted
    except InvalidToken:
        logger.error("InvalidToken - wrong key or corrupted data")
        return None
```

### 文件变更

| 文件 | 变更 |
|------|------|
| `backend/.env` | 添加 `SUPABASE_SERVICE_ROLE_KEY` |
| `app/api/routes/translate.py` | 重构 `build_llm_config()`，建立 API 优先级 |
| `app/api/routes/translate.py` | 简化 `get_user_api_config()`，移除冗余检查 |
| `app/core/encryption.py` | 增强 `decrypt_api_key()` 日志输出 |
| `frontend/src/store/useStore.ts` | 添加 `hasSystemApiKey` 状态追踪 |
| `frontend/src/components/AdvancedConfig.tsx` | 添加 API Key 已配置提示 UI |

### 验证结果

配置 `SUPABASE_SERVICE_ROLE_KEY` 后，日志确认修复成功：

```
Custom API mode: user_id=52180195-..., has_custom_api_key_in_request=False
HTTP Request: GET .../user_settings?select=... "HTTP/2 200 OK"
decrypt_api_key: Successfully decrypted API key (length=51, prefix=sk-2...)
Successfully retrieved user's custom API config for user 52180195-...
✅ Using user's stored API config from system settings
   Base URL: https://api.bltcy.ai/v1/chat/completions...
   API Key: sk-2mnLj...***
```

翻译任务成功完成：PDF 生成成功，使用的是用户系统设置中的 API Key。

### 前端 UI 改进

高级配置区域新增可视化指示：
- ✅ 当系统设置中已配置 API Key 时，显示绿色对勾图标
- 输入框 placeholder 更新为 "已在系统设置中配置"
- 用户可以在高级配置中临时覆盖系统设置

---

## UX 交互优化 (2026-02-10)

### 问题背景

用户反馈了两个前端交互体验问题：

1. **Load Source 按钮延迟无反馈**: 点击 "Load Source" 按钮后有几秒网络延迟，期间没有任何视觉反馈，用户不确定是否点击成功
2. **登录后配置未自动加载**: 用户登录后直接点击新建翻译，系统设置的默认配置未自动应用，需要先访问系统设置页面触发加载，或手动刷新页面

### 问题根因

#### Problem 1: Load Source 按钮反馈延迟

在 `Dashboard.tsx` 的 `handleLoadArxiv` 函数中，`startArxivDownload` 是异步 API 调用：

```typescript
const handleLoadArxiv = async () => {
    if (!localArxivId.trim()) return
    try {
        await startArxivDownload(localArxivId)  // ← API 请求延迟
        // startArxivDownload 内部才会设置 isDownloading = true
    } catch (e) {
        // ...
    }
}
```

在 API 响应返回前，`isDownloading` 状态未更新，按钮保持默认状态，用户无法感知点击已生效。

#### Problem 2: 登录后配置加载时机

配置加载流程：
1. Dashboard 组件挂载时，`useEffect` 调用 `loadUserSettings()`
2. `loadUserSettings()` 检查 `userSettingsLoaded` 标记，如已加载则跳过
3. 用户登录后，Dashboard 组件已挂载，`useEffect` 不会重新执行
4. `userSettingsLoaded = true`，阻止了后续重新加载

结果：登录后配置缓存未失效，需要手动访问 Settings 页面（触发 `invalidateUserSettings()`）或刷新页面。

### 解决方案

#### 1. Load Source 按钮即时反馈

**核心思路**: 添加本地 loading 状态，在 API 调用前立即更新 UI。

**代码变更** - [`Dashboard.tsx`](file:///d:/future/antigravity/LaTexTrans/frontend/src/pages/Dashboard.tsx):

```diff
+ import { toast } from 'sonner'

  export default function Dashboard() {
+     const [isLoadingSource, setIsLoadingSource] = useState(false)

      const handleLoadArxiv = async () => {
          if (!localArxivId.trim()) return
+         setIsLoadingSource(true)  // 立即设置本地状态
+         toast.info('正在加载源文件，请稍候...')  // 立即显示提示
          try {
              await startArxivDownload(localArxivId)
          } catch (e) {
              // Error handled in store
          } finally {
+             setIsLoadingSource(false)
          }
      }

      return (
          <Button
              onClick={handleLoadArxiv}
-             disabled={!localArxivId || isDownloading || (status === 'processing')}
+             disabled={!localArxivId || isLoadingSource || isDownloading || (status === 'processing')}
+             className="transition-all duration-150 active:scale-95"
          >
-             {isDownloading ? <RefreshCw .../> : <Download .../>}
+             {(isLoadingSource || isDownloading) ? <RefreshCw .../> : <Download .../>}
              Load Source
          </Button>
      )
  }
```

**效果**:
- 点击按钮瞬间触发缩放动画（`active:scale-95`）
- 按钮立即变为 disabled 状态
- 图标立即切换为旋转的 loading 图标
- Toast 通知立即显示

#### 2. 登录后自动加载配置

**核心思路**: 在 `AuthContext.signIn` 成功后，主动失效配置缓存并重新加载。

**代码变更 1** - [`useStore.ts`](file:///d:/future/antigravity/LaTexTrans/frontend/src/store/useStore.ts):

```diff
  interface TranslationState {
      // ...
-     loadUserSettings: () => Promise<void>
+     loadUserSettings: (forceReload?: boolean) => Promise<void>
  }

  export const useStore = create<TranslationState>((set, get) => ({
      // ...
-     loadUserSettings: async () => {
-         if (get().userSettingsLoaded) return
+     loadUserSettings: async (forceReload = false) => {
+         if (get().userSettingsLoaded && !forceReload) return
          // ... rest of the implementation
      }
  }))
```

**代码变更 2** - [`AuthContext.tsx`](file:///d:/future/antigravity/LaTexTrans/frontend/src/contexts/AuthContext.tsx):

```diff
+ import { toast } from 'sonner'

  const signIn = async (email: string, password: string) => {
      // ... existing code
      
      if (error) {
          setError(error.message)
+     } else {
+         // Login successful - trigger settings reload
+         try {
+             const { useStore } = await import('@/store/useStore')
+             useStore.getState().invalidateUserSettings()
+             await useStore.getState().loadUserSettings(true)
+             toast.success('系统设置已加载', {
+                 description: '您保存的默认配置已自动应用',
+                 duration: 4000,
+             })
+         } catch (e) {
+             console.warn('[Auth] Failed to load user settings after login:', e)
+         }
      }

      return { error }
  }
```

**效果**:
- 登录成功后立即失效配置缓存
- 强制重新加载用户设置（`forceReload = true`）
- 显示 Toast 通知「系统设置已加载 - 您保存的默认配置已自动应用」
- Dashboard 页面无需刷新即可使用正确配置

### 文件变更总结

| 文件 | 变更内容 |
|------|----------|
| `frontend/src/pages/Dashboard.tsx` | 添加本地 `isLoadingSource` 状态、Toast 通知、按钮动画 |
| `frontend/src/store/useStore.ts` | `loadUserSettings` 添加 `forceReload` 参数支持 |
| `frontend/src/contexts/AuthContext.tsx` | `signIn` 成功后自动加载配置并显示通知 |

### 用户体验提升

| 场景 | 改进前 | 改进后 |
|------|--------|--------|
| 点击 Load Source | 无反馈延迟 2-3 秒 | 立即显示 loading 图标 + Toast 提示 |
| 登录后新建翻译 | 使用默认配置，需手动刷新 | 自动应用保存的配置 + Toast 确认 |
| 按钮点击体验 | 静态无动画 | 缩放动画（`active:scale-95`）|


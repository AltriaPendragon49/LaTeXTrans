# 架构设计文档

## 设计目标

1. **最小侵入性** - 不破坏现有翻译和编译核心逻辑
2. **渐进式迁移** - 保留内存任务管理作为实时缓存
3. **清晰分层** - 认证、任务元数据、文件存储各司其职
4. **真实可用** - 不是 mock 或占位，而是生产级实现

## 系统分层

```
┌─────────────────────────────────────────────────────────────┐
│                      前端 (React + Vite)                     │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐ │
│  │登录页面  │  │仪表盘    │  │历史记录  │  │系统设置      │ │
│  │/login    │  │/         │  │/history  │  │/settings     │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘ │
│       │             │             │               │         │
│  ┌────┴─────────────┴─────────────┴───────────────┴───────┐ │
│  │               Supabase Client (Auth + API)              │ │
│  │               + Axios (Backend API)                     │ │
│  └─────────────────────────────────────────────────────────┘ │
└────────────────────────────┬────────────────────────────────┘
                             │ HTTP + JWT
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    后端 (FastAPI)                            │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              JWT 验证中间件 (Supabase Auth)              │ │
│  └────────────────────────────┬────────────────────────────┘ │
│                               │ user_id                      │
│  ┌────────────┬───────────────┼───────────────┬────────────┐ │
│  │ /api/arxiv │ /api/upload   │ /api/task     │/api/settings│ │
│  │ /api/trans │ /api/download │ /api/history  │             │ │
│  └─────┬──────┴───────┬───────┴───────┬───────┴──────┬─────┘ │
│        │              │               │              │        │
│  ┌─────┴──────────────┴───────────────┴──────────────┴─────┐ │
│  │                    TaskManager (重构)                    │ │
│  │  ┌─────────────────┐    ┌──────────────────────┐        │ │
│  │  │ 内存缓存层       │◄──►│ Supabase 持久化层     │        │ │
│  │  │ (实时状态)       │    │ (任务元数据)          │        │ │
│  │  └─────────────────┘    └──────────────────────┘        │ │
│  └─────────────────────────────────────────────────────────┘ │
│                               │                               │
│  ┌────────────────────────────┴────────────────────────────┐ │
│  │                  CoordinatorAgent                        │ │
│  │           (不修改，通过配置接收语言参数)                   │ │
│  └────────────────────────────┬────────────────────────────┘ │
│                               │                               │
│  ┌────────────────────────────┴────────────────────────────┐ │
│  │                 本地文件系统                             │ │
│  │        data/uploads/{task_id}/  (源文件)                 │ │
│  │        data/outputs/{task_id}/  (翻译结果)               │ │
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
        self._cache: Dict[str, TaskData] = {}  # 内存缓存
        self._supabase = get_supabase_client()  # 持久化层
    
    def create_task(self, user_id: str, ...) -> str:
        # 1. 先在 Supabase 创建记录
        record = self._supabase.table("translation_tasks").insert({
            "user_id": user_id,
            ...
        }).execute()
        
        # 2. 同时缓存到内存
        self._cache[task_id] = TaskData(...)
        
        return task_id
    
    def update_task(self, task_id: str, **kwargs):
        # 1. 更新内存缓存（实时）
        self._cache[task_id].update(**kwargs)
        
        # 2. 异步更新 Supabase（持久化）
        asyncio.create_task(self._persist_to_supabase(task_id, kwargs))
```

**优势**:
- 实时状态更新不阻塞
- 服务器重启后可从 Supabase 恢复
- 前端轮询仍然高效

### 2. JWT 验证策略

**问题**: 如何验证前端传来的 Supabase JWT？

**方案**: 后端直接调用 Supabase Auth 验证

```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def get_current_user(token: HTTPAuthorizationCredentials = Depends(security)):
    try:
        # 使用 Supabase client 验证 token
        user = supabase.auth.get_user(token.credentials)
        return user.user.id
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
```

**优势**:
- 无需自己管理密钥
- 自动处理 token 刷新验证
- 与 Supabase RLS 策略一致

### 3. 语言参数流转

**问题**: 如何确保语言参数从前端贯穿到 Agent？

**方案**: 语言参数作为一等公民

```
前端 Dashboard
    ↓ (sourceLang, targetLang)
API: POST /api/translate/{task_id}
    ↓ (request.source_language, request.target_language)
TaskManager.create_task(source_language, target_language)
    ↓ (保存到 Supabase: translation_tasks 表)
run_translation(task_id)
    ↓ (从任务记录读取语言配置)
CoordinatorAgent(config={
    "source_language": task.source_language,
    "target_language": task.target_language
})
```

**当前状态**: 
- 前端 Dashboard 已有语言选择 UI ✓
- API 已接收语言参数 ✓
- 需要添加: 持久化到 Supabase、从任务记录读取

### 4. 用户设置默认值

**问题**: 新用户如何获取默认设置？

**方案**: 懒初始化 + 数据库默认值

```python
async def get_user_settings(user_id: str):
    result = supabase.table("user_settings") \
        .select("*") \
        .eq("user_id", user_id) \
        .single() \
        .execute()
    
    if result.data is None:
        # 首次访问，创建默认设置
        default = {
            "user_id": user_id,
            "default_source_language": "en",
            "default_target_language": "zh",
            "enable_verification": True,
            "strict_mode": False
        }
        supabase.table("user_settings").insert(default).execute()
        return default
    
    return result.data
```

## 文件变更概览

### 后端新增文件

| 文件 | 用途 |
|------|------|
| `app/core/supabase_client.py` | Supabase 客户端初始化 |
| `app/core/auth.py` | JWT 验证依赖注入 |
| `app/api/routes/auth.py` | 认证相关端点（可选，主要用前端直连） |
| `app/api/routes/settings.py` | 用户设置 CRUD |
| `app/api/routes/history.py` | 翻译历史查询 |

### 后端修改文件

| 文件 | 修改内容 |
|------|----------|
| `app/services/task_manager.py` | 添加 Supabase 持久化层 |
| `app/api/routes/upload.py` | 注入 user_id |
| `app/api/routes/arxiv.py` | 注入 user_id |
| `app/api/routes/translate.py` | 注入 user_id，持久化语言参数 |
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
| `src/pages/Login.tsx` | 登录页面 |
| `src/pages/History.tsx` | 历史记录页面 |
| `src/pages/Settings.tsx` | 系统设置页面 |
| `src/components/ProtectedRoute.tsx` | 路由保护 |

### 前端修改文件

| 文件 | 修改内容 |
|------|----------|
| `src/App.tsx` | 添加路由和 AuthProvider |
| `src/lib/api.ts` | 添加认证头、新增 API 函数 |
| `src/components/app-sidebar.tsx` | 用户信息展示、登出 |

## 安全考虑

1. **RLS 策略** - 所有数据库表启用 RLS，确保用户只能访问自己的数据
2. **JWT 验证** - 后端每个请求都验证 JWT 有效性
3. **文件权限** - 下载接口验证 task 归属当前用户
4. **敏感信息** - API Key 等配置通过环境变量管理

## 向后兼容性

1. **现有翻译流程** - CoordinatorAgent 不修改，仅通过配置注入
2. **文件存储** - 保持现有路径结构不变
3. **API 端点** - 现有端点保持兼容，仅添加认证要求

## 性能考虑

1. **任务轮询** - 继续使用内存缓存，不增加数据库查询
2. **批量查询** - 历史记录支持分页，避免一次加载过多
3. **连接池** - Supabase client 使用单例，复用连接

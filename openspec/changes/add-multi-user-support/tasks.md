# 任务清单

## 阶段 1: Supabase 基础设施

### 1.1 数据库表创建
- [x] 创建 `user_settings` 表（含完整配置字段）
- [x] 创建 `translation_tasks` 表（含配置快照字段）
- [x] 配置 RLS 策略
- [ ] 验证表结构和权限

### 1.2 后端 Supabase 集成
- [x] 安装 supabase-py 依赖
- [x] 创建 `app/core/supabase_client.py` 配置模块
- [x] 添加 Supabase 环境变量配置
- [ ] 测试 Supabase 连接

---

## 阶段 2: 用户认证

### 2.1 后端认证
- [x] 创建 `app/core/auth.py` 可选 JWT 验证依赖
- [x] 实现 `get_optional_user()` 函数（支持访客模式）
- [x] **重构为纯 RLS 模式**（2026-02-08）
  - [x] 删除 `auth.get_user()` 调用，解决 Invalid API key 问题
  - [x] 实现 `create_supabase_client_with_token()` token 透传
  - [x] 更新 `settings.py` 使用纯 RLS
  - [x] 更新 `history.py` 使用纯 RLS
  - [x] 添加数据库迁移：`user_id DEFAULT auth.uid()`
  - [x] 添加 `supabase_anon_key` 配置
  - [ ] 验证依赖兼容性（supabase/httpx 版本）
- [ ] 更新 CORS 配置支持 credentials


### 2.2 前端认证
- [x] 安装 @supabase/supabase-js
- [x] 创建 `src/lib/supabase.ts` 客户端配置
- [x] 创建 `src/contexts/AuthContext.tsx`
- [x] 创建 `src/hooks/useAuth.ts`（集成在 AuthContext 中）
- [x] 创建登录/注册页面 `/login`
  - [x] 邮箱密码登录表单
  - [x] 邮箱密码注册表单
  - [x] 登录/注册切换
- [x] 更新 `src/lib/api.ts` 可选携带 JWT

### 2.3 用户资料页面
- [x] 创建 `src/pages/Profile.tsx`
- [x] 显示当前登录邮箱（不可编辑）
- [x] 登出按钮
- [x] 退出登录 toast 反馈（修复于 2026-02-08）
- [x] 更新侧边栏 User Profile 链接

---

## 阶段 3: 系统设置

### 3.1 后端设置 API
- [x] 创建 `app/api/routes/settings.py`
- [x] GET /api/settings - 获取用户设置（需认证）
- [x] PUT /api/settings - 更新用户设置（需认证）
- [x] 首次访问时自动创建默认设置

### 3.2 前端设置页面
- [x] 创建 `src/pages/Settings.tsx`
- [x] 未登录时显示"请登录"提示
- [x] 已登录时显示设置表单
  - [x] 源语言 / 目标语言选择
  - [x] 翻译模式选择（全文翻译 / 快速筛查）
  - [x] 编译策略选择（自动 / PDFLaTex / XeLaTex / LuaLaTex）
  - [x] 翻译模型选择
  - [x] 验证代理开关（默认开启）
  - [x] 生成术语表开关（默认开启）
  - [x] 使用作者默认 API 开关（默认开启）
  - [x] 自定义 Base URL 输入框（关闭默认 API 时显示）
  - [x] 自定义 API Key 输入框（关闭默认 API 时显示）
- [x] 保存按钮触发 API 更新
- [x] Toast 反馈保存结果

---

## 阶段 4: 翻译历史

### 4.1 后端任务持久化
- [ ] 重构 `TaskManager` 支持双层存储
  - 内存缓存用于所有任务（含访客）
  - Supabase 持久化仅用于登录用户
- [ ] 更新 `create_task` 方法：
  - 接收完整配置参数
  - 已登录：保存配置快照到 Supabase
  - 未登录：仅内存存储
- [ ] 更新 `update_task` 方法同步到 Supabase
- [x] 创建 `app/api/routes/history.py`
- [x] GET /api/history - 获取用户任务列表（需认证、分页）
- [x] GET /api/history/{task_id} - 获取任务详情（需认证）

### 4.2 前端历史记录页面
- [x] 创建 `src/pages/History.tsx`
- [x] 未登录时显示"请登录"提示
- [x] 已登录时显示任务列表
  - [x] 显示 arXiv ID / 上传文件标识
  - [x] 显示翻译模式、状态、创建时间
  - [x] 分页加载
  - [ ] 状态筛选（可选）
- [ ] 任务详情弹窗/页面
  - [ ] 显示配置快照
  - [ ] 预览/下载译文 PDF
  - [ ] 下载源 PDF（如有）

---

## 阶段 5: 配置继承

### 5.1 前端配置加载
- [x] 更新 Dashboard 页面加载逻辑
  - [x] 已登录用户：从 /api/settings 读取默认配置
  - [x] 未登录用户：使用系统默认值
- [x] 高级配置 UI 预填充用户默认值
- [x] 新建翻译时配置同步（修复于 2026-02-08）
- [x] Settings 页面添加"刷新页面后生效"提示（修复于 2026-02-09）
- [x] 翻译时自动读取用户加密 API Key（修复于 2026-02-09）
- [x] 高级配置 API Key 输入框添加已配置提示（修复于 2026-02-09）

### 5.2 UX 交互改进（2026-02-10）
- [x] Load Source 按钮即时反馈
  - [x] 添加本地 loading 状态（`isLoadingSource`）
  - [x] 点击时立即显示 Toast 提示
  - [x] 添加按钮缩放动画（`active:scale-95`）
- [x] 登录后自动加载配置
  - [x] AuthContext.signIn 成功后调用 loadUserSettings
  - [x] useStore.loadUserSettings 支持 forceReload 参数
  - [x] 显示 Toast 通知用户配置已加载

### 5.2 后端配置传递
- [x] 确保翻译请求正确接收完整配置
- [ ] 配置快照保存到 translation_tasks 表（TaskManager 重构待完成）

---

## 阶段 6: 验证与文档

### 6.1 集成验证
- [x] 访客模式测试：未登录创建翻译 → 成功执行 → 刷新页面后任务丢失
- [x] 注册流程测试：邮箱注册 → 确认邮件 → 登录
- [x] 登录流程测试：邮箱登录 → 查看历史
- [x] 设置保存测试：修改设置 → 新建翻译时自动填充（2026-02-09 验证通过）
- [ ] 持久化测试：服务器重启后登录用户任务保留
- [ ] 下载权限测试：用户只能下载自己的任务文件
- [ ] 退出登录反馈测试：点击退出 → toast 提示 → 跳转首页

### 6.2 文档更新
- [ ] 更新 backend/README.md（Supabase 配置说明）
- [ ] 更新 frontend/README.md（认证流程说明）
- [ ] 创建部署指南（环境变量配置）

---

## 依赖关系

```mermaid
graph TD
    A[1.1 数据库表] --> B[1.2 后端集成]
    B --> C[2.1 后端认证]
    C --> D[2.2 前端认证]
    D --> E[2.3 用户资料]
    C --> F[3.1 设置 API]
    F --> G[3.2 设置页面]
    B --> H[4.1 任务持久化]
    D --> I[4.2 历史记录页面]
    H --> I
    G --> J[5.1 前端配置加载]
    J --> K[5.2 后端配置传递]
    E --> L[6.1 验证]
    I --> L
    K --> L
```

## 访客模式与登录用户对比

| 功能 | 访客用户 | 登录用户 |
|------|----------|----------|
| 新建翻译（ArXiv / 拖拽上传） | ✅ | ✅ |
| 高级配置调整 | ✅ | ✅ |
| 翻译执行与预览 | ✅ | ✅ |
| 下载 PDF / 源文件 | ✅ | ✅ |
| 翻译历史记录 | ❌ | ✅ |
| 系统设置保存 | ❌ | ✅ |
| 配置自动填充 | ❌ | ✅ |
| 任务持久化 | ❌ | ✅ |

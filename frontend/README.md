# LaTeXTrans 前端应用

LaTeX论文自动翻译系统的Web前端,基于 React + TypeScript + Vite 构建。支持用户注册登录、翻译历史管理、系统设置持久化和访客模式。

## 🚀 快速开始

### 1. 安装依赖

```bash
cd frontend
npm install
```

### 2. 开发模式

```bash
npm run dev
```

访问 http://localhost:5173

### 3. 生产构建

```bash
npm run build
npm run preview
```

## ✨ 主要功能

### 📦 多种输入方式

#### 1. ArXiv ID 输入
- 输入 arXiv 论文 ID（如 `2508.18791`）
- 自动下载论文源码并准备翻译
- 支持自动检测并显示原文 PDF 预览

#### 2. 拖拽上传
- **支持文件夹拖拽**: 直接拖拽包含 `.tex` 文件的文件夹
- **支持压缩包**: 支持 `.zip`, `.tar.gz`, `.rar` 格式
- **自动校验**: 上传后自动检测主入口文件和 LaTeX 结构
- **实时反馈**: 显示文件数量、主文件名、校验结果

### ⚙️ 高级配置选项

点击"高级配置"展开以下选项：

#### 翻译模式
- **全文翻译**: 翻译整篇论文的所有内容
- **文献快速筛查**: 仅翻译摘要(Abstract)和结论(Conclusion)部分，适合快速了解论文核心内容

#### 编译策略
- **自动**: 智能选择 pdflatex 或 xelatex 或 lualatex
- **pdflatex**: 适用于大多数英文论文
- **xelatex**: 支持中文和Unicode字符
- **lualatex**: 支持中文和Unicode字符

#### 翻译模型
- 选择不同的 LLM 模型（如 `gpt-4.1-mini`, `deepseek` 等）
- 根据需求平衡速度和质量

#### 其他选项
- **启用验证代理**: 额外的翻译质量检查（更慢但更准确）
- **生成术语表**: 自动生成专业术语对照表（Source Term ↔ Translation）

#### 自定义 API
- **自定义 API Key**: 使用您自己的 LLM API 密钥
- **自定义 Base URL**: 支持任何兼容 OpenAI 格式的 API 端点

### 📊 翻译结果查看

#### PDF 对比查看
- **分屏模式**: 左侧原文，右侧译文，支持拖拽调整比例
- **单屏模式**: 仅显示译文 PDF
- **实时预览**: PDF 在浏览器内直接显示，无需下载

#### 术语表查看
- 点击工具栏中的 **"术语表"** 按钮
- 侧边栏展示所有提取的专业术语及翻译
- 支持单独下载 CSV 格式术语表

#### 实时日志
- 查看翻译进度和详细日志
- 实时更新翻译状态

### 🔐 用户认证

- **邮箱注册/登录**: 基于 Supabase Auth
- **访客模式**: 未登录用户可使用临时翻译（不持久化）
- **自动配置加载**: 登录后自动应用用户保存的默认配置
- **会话管理**: JWT 自动刷新，支持登出

### 📋 翻译历史

- 查看所有翻译任务记录及配置快照
- 点击历史任务直接预览 PDF 或查看进度
- 支持单条删除（含处理中任务中断）和批量删除
- 可折叠配置详情展示

### ⚙️ 系统设置

- 保存个人默认翻译配置（语言、模型、编译策略等）
- 新建翻译时自动填充已保存的配置
- 支持自定义 API Key（AES-256 加密存储）

### 💾 下载选项
- **译文 PDF**: 翻译后的完整 PDF
- **译文源码**: 翻译后的 LaTeX 源文件（ZIP 压缩包）
- **术语表**: CSV 格式的术语对照表
- **编译日志**: LaTeX 编译日志（用于调试）

## 📁 项目结构

```
frontend/
├── src/
│   ├── components/          # React 组件
│   │   ├── AdvancedConfig.tsx    # 高级配置面板
│   │   ├── DropZone.tsx          # 拖拽上传组件
│   │   ├── TerminologyTable.tsx  # 术语表侧边栏
│   │   ├── ui/                   # shadcn/ui 基础组件
│   │   └── ...
│   ├── pages/               # 页面组件
│   │   ├── Dashboard.tsx         # 主页面（输入+配置）
│   │   ├── Processing.tsx        # 处理中页面（进度+日志）
│   │   ├── Comparisons.tsx       # 结果页面（PDF对比+下载）
│   │   ├── Login.tsx             # 登录/注册页面
│   │   ├── Profile.tsx           # 用户资料页面
│   │   ├── Settings.tsx          # 系统设置页面
│   │   └── History.tsx           # 翻译历史页面
│   ├── contexts/            # React Context
│   │   └── AuthContext.tsx       # 认证上下文（Supabase Auth）
│   ├── store/               # 状态管理 (zustand)
│   │   └── useStore.ts           # 全局状态（含用户配置加载）
│   ├── types/               # TypeScript 类型定义
│   │   └── config.ts             # 配置相关类型
│   ├── lib/
│   │   ├── api.ts                # API 调用封装（含可选JWT）
│   │   ├── supabase.ts           # Supabase 客户端配置
│   │   └── utils.ts              # 工具函数
│   ├── App.tsx              # 应用入口
│   └── main.tsx             # Vite 入口
├── package.json
└── vite.config.ts
```

## 🛠️ 技术栈

- **构建工具**: Vite 6.x
- **框架**: React 19.x
- **语言**: TypeScript 5.x
- **状态管理**: Zustand
- **UI 组件**: shadcn/ui + Radix UI
- **样式**: Tailwind CSS 4.x
- **图标**: Lucide React
- **认证**: Supabase Auth (@supabase/supabase-js)

## 🔗 API 集成

前端通过 `src/lib/api.ts` 与后端通信，主要端点：

- `POST /api/arxiv` - 下载 arXiv 论文（可选JWT）
- `POST /api/upload` - 上传本地文件（可选JWT）
- `POST /api/translate/{task_id}` - 启动翻译
- `GET /api/task/{task_id}` - 查询进度
- `GET /api/download/{task_id}/pdf` - 下载译文 PDF
- `GET /api/download/{task_id}/terminology` - 下载术语表
- `GET /api/preview/{task_id}/source-pdf` - 预览原文 PDF
- `GET /api/settings` - 获取用户设置（需JWT）
- `PUT /api/settings` - 更新用户设置（需JWT）
- `GET /api/history` - 获取翻译历史（需JWT）
- `DELETE /api/history/{task_id}` - 删除历史记录（需JWT）

## 📝 配置说明

### 环境变量

创建 `.env` 文件（可选）：

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
```

> **注意**: Supabase 环境变量为多用户功能必需。未配置时认证相关功能不可用。

### 高级配置默认值

配置项的默认值定义在 `src/types/config.ts`：

```typescript
export const DEFAULT_ADVANCED_CONFIG: AdvancedConfig = {
    translation_mode: 'full',           // 全文翻译
    compile_strategy: 'auto',           // 自动选择编译器
    enable_verification: true,          // 启用验证代理
    translation_model: 'gpt-4.1-mini',  // 默认模型
    generate_terminology_table: true,   // 生成术语表
    use_author_api: true,               // 使用默认 API
    custom_base_url: undefined,         // 自定义 URL
    custom_api_key: undefined           // 自定义 Key
}
```

## 🐛 故障排除

### 无法连接后端

确保后端服务在正确端口运行：
```bash
cd backend
python -m uvicorn backend.app.main:app --port 8000
```

### CORS 错误

后端需要允许前端 origin，检查 `backend/app/main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    ...
)
```

### 拖拽上传无反应

- 确保浏览器支持拖拽 API（现代浏览器均支持）
- 检查控制台是否有报错信息
- 尝试先压缩文件夹为 `.zip` 再上传

## 📚 更多资源

- **后端文档**: `backend/README.md`
- **OpenSpec 变更记录**: `openspec/changes/archive/`
- **UI 组件文档**: https://ui.shadcn.com/
- **Supabase 文档**: https://supabase.com/docs

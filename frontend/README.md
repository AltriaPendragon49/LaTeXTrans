# PaperX Frontend

基于 React 19 + TypeScript + Vite 7 构建的 PaperX 前端应用，提供论文翻译、社区浏览、术语管理、AI 对话等完整用户界面。

## 技术栈

| 类别 | 技术 |
|------|------|
| 框架 | React 19, TypeScript 5.9 |
| 构建 | Vite 7 |
| 样式 | TailwindCSS 4, tailwind-merge, class-variance-authority |
| UI 组件 | shadcn/ui (Radix UI), lucide-react |
| 路由 | React Router 7 |
| 状态管理 | Zustand 5 |
| HTTP | Axios |
| 国际化 | i18next, react-i18next |
| PDF 预览 | react-pdf 10 |
| 动画 | framer-motion, lottie-react |
| 数学渲染 | KaTeX |
| 测试 | Vitest 4, Testing Library, jsdom |
| 校验 | ESLint 9, TypeScript strict |

## 环境配置

```env
# .env.development
VITE_API_BASE_URL=http://localhost:8000/api
```

```env
# .env.production
VITE_API_BASE_URL=/api
```

## 项目结构

```
frontend/
├── src/
│   ├── App.tsx                    # 根组件，路由定义
│   ├── main.tsx                   # 应用入口
│   ├── layout.tsx                 # 主布局（侧边栏 + 内容区）
│   ├── layout/                    # 布局组件
│   │   ├── AppSidebar.tsx         # 侧边导航栏
│   │   └── shell-navigation.tsx   # 导航配置
│   ├── contexts/
│   │   └── AuthContext.tsx        # 认证上下文（登录/注册/会话）
│   ├── theme/
│   │   └── theme-provider.tsx     # 亮色/暗色主题
│   ├── features/                  # 业务功能模块
│   │   ├── admin-curation/        # 管理员策展
│   │   │   ├── components/        # AdminCurationWorkspace, AdminCurationTasksWorkspace
│   │   │   ├── services/          # admin-curation-api.ts
│   │   │   └── utils/             # admin-access.ts
│   │   ├── auth-shell/            # 认证界面
│   │   │   └── components/        # LoginPrompt, LoginWorkspace
│   │   ├── community-conversation/ # AI 学术对话
│   │   │   ├── components/        # ConversationComposer, ConversationRail, ConversationThread
│   │   │   ├── services/          # community-conversation-api.ts
│   │   │   └── utils/             # conversation-records.ts, conversation-runtime.ts
│   │   ├── community-paper/       # 社区论文
│   │   │   ├── components/        # PaperCard, PaperDetailHeader/Screen/Workspace,
│   │   │   │                       # CommunityFeedSurface, CommunitySubmitPanel, FavoritePicker,
│   │   │   │                       # HotWindowFilter, PaperPreviewReader, PaperStatusBadge 等
│   │   │   ├── hooks/             # useCommunityPapers, use-paper-detail
│   │   │   ├── services/          # community-paper-api.ts
│   │   │   └── utils/             # paper-detail-mode-resolution.ts
│   │   ├── rag-terminology/       # RAG 术语管理
│   │   │   ├── components/        # TermFormModal, TerminologyBrowserPage, TerminologyMatchLog,
│   │   │   │                       # TerminologyReviewPanel
│   │   │   ├── hooks/             # useDomains
│   │   │   ├── services/          # rag-terminology-api.ts
│   │   │   └── types.ts
│   │   ├── translation-workflow/  # 翻译工作流
│   │   │   ├── components/        # TranslationWorkspace, ProcessingWorkspace, ComparisonWorkbench,
│   │   │   │                       # DropZone, AdvancedConfig, FormattingPanel, TerminologyTable,
│   │   │   │                       # ProcessingLogViewer, BatchTranslation, PdfDirectWorkspace
│   │   │   ├── hooks/             # useTranslationConfig, useTranslationTask
│   │   │   └── store/             # useTranslationStore (Zustand)
│   │   └── user-workspace/        # 用户工作区
│   │       ├── accountIdentity.ts  # 账户身份工具
│   │       └── components/        # HistoryWorkspace, ProfileWorkspace, GlossaryWorkspace,
│   │                               # TranslationSettingsWorkspace, WorkspaceAccountMenu
│   ├── pages/                     # 页面入口
│   │   ├── home/                  # 首页（含 HomeFeedSection）
│   │   ├── login/                 # 登录页
│   │   ├── translate/             # 翻译页
│   │   ├── processing/            # 处理进度页
│   │   ├── preview/               # PDF 预览页
│   │   ├── paper-detail/          # 论文详情页
│   │   ├── tools-hub/             # 工具中心页
│   │   ├── favorites/             # 收藏页
│   │   ├── profile/               # 个人资料页
│   │   ├── workspace-history/     # 翻译历史页
│   │   ├── workspace-settings/    # 翻译设置页
│   │   ├── workspace-glossary/    # 术语表页
│   │   ├── community-conversation/  # AI 对话页
│   │   ├── community-admin-curation/          # 管理员策展页
│   │   ├── community-admin-curation-tasks/    # 策展任务列表页
│   │   └── rag-terminology-admin/            # RAG 术语后台页
│   ├── ui/                        # 通用 UI 组件库（40+ 组件）
│   │   ├── primitives/            # Radix 封装（Button, Badge, Dialog, Tabs 等 18 个）
│   │   ├── button/ card/ input/   # 基础组件
│   │   ├── chat-bubble/           # 聊天气泡
│   │   ├── data-table/            # 数据表格
│   │   ├── filter-toolbar/        # 筛选工具栏
│   │   ├── language-selector/     # 语言选择器
│   │   ├── loading-state/         # 加载状态
│   │   ├── search-bar/            # 搜索框
│   │   ├── sidebar-shell/         # 侧边栏外壳
│   │   ├── status-badge/          # 状态标签
│   │   ├── upload-card/           # 上传卡片
│   │   └── workflow-stepper/      # 工作流步骤器
│   ├── lib/                       # 工具库
│   │   ├── api.ts                 # Axios 实例与请求封装
│   │   ├── local-auth.ts          # 本地认证客户端
│   │   ├── community-api.ts       # 社区 API 客户端
│   │   ├── community-agent-conversations.ts  # 对话管理
│   │   ├── paper-preview-enhancer.ts  # PDF 预览增强
│   │   ├── paper-reader-html.ts   # 论文阅读器 HTML 生成
│   │   ├── network-retry.ts       # 网络重试策略
│   │   └── utils.ts               # 通用工具
│   ├── hooks/                     # 全局 Hooks
│   │   ├── use-mobile.tsx         # 移动端检测
│   │   └── use-task-status-sse.ts # 任务状态 SSE 订阅
│   ├── i18n/                      # 国际化
│   │   ├── config.ts              # i18next 配置
│   │   ├── ui-text.ts             # UI 文案辅助
│   │   ├── task-copy.ts           # 任务相关文案
│   │   └── formatting-copy.ts     # 格式文案
│   ├── locales/                   # 8 语言翻译文件
│   │   └── en/ zh/ ja/ ko/ de/ fr/ es/ ru/
│   ├── types/                     # TypeScript 类型
│   │   ├── community.ts           # 社区类型
│   │   ├── config.ts              # 配置类型
│   │   └── katex-auto-render.d.ts # KaTeX 声明
│   └── test/                      # 测试基础设施
│       ├── setup.ts               # 测试环境配置
│       ├── theme.ts               # 主题测试工具
│       └── viewport.ts            # 视口测试工具
├── scripts/i18n/                  # i18n 检查/同步脚本
├── functions/                     # Cloudflare Functions
├── vite.config.ts                 # Vite 配置
├── tailwind.config.js             # Tailwind 配置
├── vitest.config.ts               # Vitest 配置
├── components.json                # shadcn/ui 配置
├── tsconfig.json                  # TypeScript 配置
├── package.json                   # 依赖与脚本
└── index.html                     # 入口 HTML
```

## 路由设计

| 路径 | 页面 | 权限 |
|------|------|------|
| `/` | 首页（社区 Feed） | 公开 |
| `/login` | 登录/注册 | 公开 |
| `/paper/:paperId` | 论文详情 | 公开 |
| `/preview` | PDF 预览 | 公开 |
| `/processing` | 翻译进度 | 公开 |
| `/tools` | 工具中心 | 公开 |
| `/translate` | 翻译页 | 需登录 |
| `/workspace/history` | 翻译历史 | 需登录 |
| `/workspace/settings` | 翻译设置 | 需登录 |
| `/workspace/glossary` | 术语表 | 需登录 |
| `/favorites` / `/favorites/:folderId` | 收藏夹 | 需登录 |
| `/profile` | 个人资料 | 需登录 |
| `/agent[/:conversationId]` | AI 对话 | 管理员 |
| `/admin/curation` | 策展管理 | 管理员 |
| `/admin/curation/tasks` | 策展任务 | 管理员 |
| `/admin/rag-terminology` | 术语后台 | 管理员 |

## 核心功能模块说明

### 翻译工作流 (translation-workflow)

核心翻译功能，支持三种输入：
1. **上传 .tex 文件**：拖拽 `.tex` 文件或 `.zip`/`.tar.gz` 压缩包
2. **arXiv ID 获取**：输入 arXiv ID 自动下载源码
3. **批量翻译**：多文件同时提交

包含组件：TranslationWorkspace（翻译输入）、ProcessingWorkspace（进度监控）、ComparisonWorkbench（结果对比）、AdvancedConfig（高级配置）、DropZone（拖拽上传）、PdfDirectWorkspace（PDF 直译）、BatchTranslation（批量翻译）

### 社区论文 (community-paper)

论文社区功能：
- **Feed 流**：按热度/时间浏览已发布论文，支持热榜窗口筛选（24h/7d/30d）
- **论文详情**：结构化内容解读、PDF 预览、源码/译文下载
- **收藏系统**：创建文件夹、管理收藏
- **互动**：点赞、浏览计数
- **论文提交**：用户提交 arXiv 论文

### 管理员策展 (admin-curation)

- 策展管理：审核和发布论文
- 任务监控：查看进度、失败原因
- 硬删除：批量管理策展任务

### RAG 术语管理 (rag-terminology)

- 术语浏览（含 ~50 个学科领域筛选）
- 术语审核（管理员审批/拒绝）
- 匹配日志查看
- CSV/BibTeX 批量导入

### AI 学术对话 (community-conversation)

- 对话式论文检索
- 学术问答
- 论文导入与翻译触发

## 开发命令

```bash
npm run dev          # 启动开发服务器
npm run build        # 生产构建
npm run lint         # ESLint 检查
npm run test         # 运行测试
npm run test:watch   # 测试监听
npm run test:coverage # 测试覆盖率
npm run i18n:check   # 检查翻译文件完整性
npm run i18n:sync    # 同步缺失翻译
npm run preview      # 预览生产构建
```

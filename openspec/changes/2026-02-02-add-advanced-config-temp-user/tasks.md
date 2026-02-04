# 任务清单

## 阶段 1: 数据模型与类型定义

### 1.1 前端类型定义
- [x] 创建 `src/types/config.ts` 定义高级配置类型
- [x] 更新 `src/store/useStore.ts` 添加配置状态管理
- [x] 添加默认配置常量

### 1.2 后端数据模型
- [x] 创建 `app/models/config_models.py` 定义 `AdvancedConfig`
- [x] 定义 `SourceType` 枚举（含 `folder_upload`）
- [x] 创建 `LatexValidation` 校验结果模型

---

## 阶段 2: 高级配置 UI

### 2.1 高级配置组件
- [x] 创建 `src/components/AdvancedConfig.tsx` 组件
  - [x] 翻译模式选择（全文/摘要/术语优先）
  - [x] 编译策略选择（pdflatex/xelatex/自动）
  - [x] 启用验证代理开关
  - [x] 生成双语 PDF 开关
  - [x] 翻译模型选择
  - [x] 自定义 API Key 输入（可选）
- [x] 组件使用 zustand store 管理状态

### 2.2 Dashboard 集成
- [x] 修改 `Dashboard.tsx` 替换现有占位高级配置
- [x] 集成 `AdvancedConfig` 组件到 Collapsible 区域
- [x] 确保配置与翻译按钮联动

---

## 阶段 3: 拖拽上传 UI

### 3.1 DropZone 组件
- [x] 创建 `src/components/DropZone.tsx` 组件
  - [x] 拖拽进入/离开视觉反馈
  - [x] 支持文件夹拖拽（UI提示压缩）
  - [x] 支持 ZIP 文件拖拽
  - [x] 显示已选择的文件/文件夹信息
- [x] 拖拽后展示：文件数量、是否检测到 .tex 文件

### 3.2 Dashboard 集成
- [x] 在 Dashboard 添加拖拽上传区域（ArXiv 输入下方）
- [x] 拖拽后保存到 store，等待用户点击"开始翻译"
- [x] 支持切换 ArXiv ID / 拖拽文件两种输入模式

---

## 阶段 4: 后端配置参数支持

### 4.1 翻译请求扩展
- [x] 修改 `TranslateRequest` 包含 `AdvancedConfig`
- [x] 更新 `/api/translate/{task_id}` 接收完整配置
- [x] 将配置参数映射到 `agent_config`

### 4.2 任务记录扩展
- [x] 修改 `TaskManager.create_task()` 接受 `advanced_config`
- [x] 任务记录中存储完整配置快照
- [x] `/api/task/{task_id}` 返回配置信息

---

## 阶段 5: 目录上传与校验

### 5.1 LaTeX 目录校验
- [x] 创建 `app/services/latex_validator.py`
  - [x] `validate_latex_directory()` 校验函数
  - [x] 检测 .tex 文件存在性
  - [x] 检测主入口文件（main.tex 或 `\documentclass`）
  - [x] 返回校验结果（包含警告/错误）

### 5.2 上传接口扩展
- [x] 修改 `POST /api/upload` 支持目录上传
- [x] 支持多种压缩格式自动解压（ZIP/TAR.GZ/RAR）
- [x] 上传后调用 LaTeX 校验
- [x] 返回校验结果给前端

---

## 阶段 6: 前后端联调

### 6.1 API 集成
- [x] 更新 `src/lib/api.ts` 传递完整配置
- [x] 上传接口支持 multipart/form-data + 配置参数
- [x] 验证配置正确传递到后端

### 6.2 翻译流程测试
- [x] 验证 ArXiv ID + 高级配置 → 翻译成功
- [x] 验证拖拽上传 + 高级配置 → 翻译成功
- [x] 验证配置刷新页面后重置

---

## 阶段 7: 验证与文档

### 7.1 功能验证
- [ ] 高级配置所有选项真实影响翻译行为
- [x] 拖拽上传 LaTeX 目录 → 校验 → 翻译 → 下载
- [x] 拖拽上传 ZIP → 解压 → 校验 → 翻译 → 下载
- [x] 无效目录（无 .tex 文件）返回明确错误

### 7.2 配置持久化验证
- [x] 刷新页面后配置重置为默认值
- [ ] 任务记录中保留创建时的配置快照

### 7.3 文档更新
- [ ] 更新 frontend/README.md
- [ ] 更新 backend/README.md

---

## 阶段 8: UX 改进（补充）

> 来源：Fixing Source PDF Preview 对话会话

### 8.1 Source PDF 预览修复
- [x] 后端添加 `/preview/{task_id}/source-pdf` 端点
- [x] 实现 4 层策略：arxiv_id → 目录名提取 → 现有 PDF → 编译源 tex
- [x] 任务管理器添加 `arxiv_id` 字段
- [x] arXiv 下载时存储 `arxiv_id`
- [x] 前端 `Comparisons.tsx` 更新 sourceUrl 逻辑

### 8.2 Live Logs 简化
- [x] 移除时间戳显示（时间戳实时变动问题）
- [x] 简化 `log-viewer.tsx` 只显示纯日志

### 8.3 默认配置更新
- [x] `bilingual_output` 默认值改为 `true`
- [x] `translation_model` 默认值改为 `'gpt-4.1-mini'`

### 8.4 任务重置逻辑修复
- [x] `startArxivDownload` 开始时调用 `reset()` 清空旧状态
- [x] 下载成功后设置 `status: 'ready'` 使 Start 按钮可用
- [x] `DropZone.processFile` 开始时调用 `reset()`


## 依赖关系

```mermaid
graph TD
    A[1.1 前端类型] --> C[2.1 高级配置组件]
    A --> D[3.1 DropZone 组件]
    B[1.2 后端数据模型] --> E[4.1 翻译请求扩展]
    B --> F[5.1 LaTeX 校验]
    C --> G[2.2 Dashboard 集成]
    D --> H[3.2 Dashboard 集成]
    E --> I[4.2 任务记录扩展]
    F --> J[5.2 上传接口扩展]
    G --> K[6.1 API 集成]
    H --> K
    I --> K
    J --> K
    K --> L[6.2 翻译流程测试]
    L --> M[7.1 功能验证]
```

## 阶段与人员分配

| 阶段 | 预估时间 | 可并行 |
|------|----------|--------|
| 阶段 1: 数据模型 | 0.5 天 | ✅ 前后端可并行 |
| 阶段 2: 高级配置 UI | 1 天 | ✅ 可与阶段 4 并行 |
| 阶段 3: 拖拽上传 UI | 1 天 | ✅ 可与阶段 5 并行 |
| 阶段 4: 后端配置支持 | 0.5 天 | ✅ 可与阶段 2 并行 |
| 阶段 5: 目录上传校验 | 1 天 | ✅ 可与阶段 3 并行 |
| 阶段 6: 联调 | 1 天 | ❌ 依赖前面阶段 |
| 阶段 7: 验证文档 | 0.5 天 | ❌ 依赖阶段 6 |

**总预估**: 3-4 天（并行开发）

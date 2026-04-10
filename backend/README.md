# LaTeXTrans 后端API服务

LaTeX论文自动翻译系统的Web后端服务,基于FastAPI构建。

## 📋 目录

- [快速开始](#快速开始)
- [系统要求](#系统要求)
- [API端点](#api端点)
- [使用示例](#使用示例)
- [项目结构](#项目结构)
- [配置说明](#配置说明)
- [故障排除](#故障排除)

## 🚀 快速开始

### 1. 安装依赖

```bash
# 从项目根目录执行
pip install -r backend/requirements.txt
```

### 2. 启动服务

**Windows:**
```bash
cd backend
start.bat
```

**Linux/Mac:**
```bash
cd backend
chmod +x start.sh
./start.sh
```

**手动启动(推荐用于开发):**
```bash
# 从项目根目录执行
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 9001 --reload
```

### 3. 访问服务

启动成功后访问:
- **API文档(Swagger)**: http://localhost:9001/docs
- **API文档(ReDoc)**: http://localhost:9001/redoc
- **健康检查**: http://localhost:9001/health

## 💻 系统要求

### 必需
- **Python**: >= 3.10
- **LaTeX发行版**: TexLive 2024+ 或 MiKTeX (需包含 `pdflatex` 和 `xelatex`)
- **系统工具**: `tar`, `gzip` (Linux/Mac自带, Windows需配置Git Bash或WSL)

### 推荐
- **内存**: >= 8GB
- **磁盘空间**: >= 5GB (用于存储上传文件和输出)

## 📡 API端点

### 核心端点

#### `GET /health`
健康检查端点

**响应示例:**
```json
{
  "status": "healthy",
  "app": "LaTeXTrans Backend",
  "version": "1.0.0",
  "timestamp": "2026-01-28T01:00:00"
}
```

#### `POST /upload`
上传LaTeX文件

**请求:**
- **Content-Type**: `multipart/form-data`
- **文件类型**: `.tex`, `.zip`, `.tar`, `.tar.gz`

**响应:**
```json
{
  "task_id": "abc123...",
  "status": "pending",
  "message": " Files uploaded successfully",
  "file_count": 5
}
```

#### `POST /arxiv`
从arXiv下载论文源码

**请求:**
```json
{
  "arxiv_id": "2508.18791"
}
```

**响应:**
```json
{
  "task_id": "xyz789...",
  "arxiv_id": "2508.18791",
  "status": "success",
  "message": "arXiv source downloaded",
  "file_count": 12
}
```

#### `POST /translate/{task_id}`
启动翻译任务

**请求:**
```json
{
  "target_language": "zh",
  "source_language": "en",
  "advanced_config": {
    "translation_mode": "full",
    "compile_strategy": "auto",
    "enable_verification": true,
    "translation_model": "gpt-4.1-mini",
    "generate_terminology_table": true,
    "use_author_api": true,
    "custom_base_url": null,
    "custom_api_key": null,
    "typography": {
      "line_spacing": 1.5,
      "font_size": 11,
      "enable_two_column": false
    },
    "enable_email_notification": true
  }
}
```

**高级配置说明：**
- `translation_mode`: 翻译模式
  - `"full"`: 全文翻译
  - `"quick_scan"`: 快速筛查（仅摘要和结论）
- `compile_strategy`: PDF 编译策略
  - `"auto"`: 自动选择（默认）
  - `"pdflatex"`: 使用 pdflatex
  - `"xelatex"`: 使用 xelatex
- `enable_verification`: 是否启用翻译质量验证
- `translation_model`: LLM 模型名称
- `generate_terminology_table`: 是否生成术语对照表
- `use_author_api`: 是否使用默认 API (false 时使用自定义 API)
- `custom_base_url`: 自定义 API 端点（可选）
- `custom_api_key`: 自定义 API 密钥（可选）
- `typography`: 进阶排版配置 (可选)
  - `line_spacing`: 行距 (例如 1.5)
  - `font_size`: 字号 (例如 11)
  - `enable_two_column`: 双栏排版
- `enable_email_notification`: 任务完成/失败时是否发送邮件通知

**响应:**
```json
{
  "task_id": "abc123...",
  "status": "started",
  "message": "Translation started in background"
}
```

#### `GET /task/{task_id}`
查询任务状态

**响应:**
```json
{
  "task_id": "abc123...",
  "status": "processing",
  "progress": 45,
  "stage": "translating",
  "message": "Translating section: Introduction",
  "error": null,
  "warnings": null,
  "source_available": true,
  "created_at": "2026-01-28T01:00:00",
  "completed_at": null
}
```

**状态值说明:**
- `pending`: 等待处理
- `processing`: 正在处理
- `completed`: 成功完成
- `completed_with_warnings`: 完成但有警告
- `failed_compilation`: 编译失败
- `failed`: 其他失败

#### `GET /download/{task_id}/pdf`
下载翻译后的PDF

**响应:** PDF文件流

#### `GET /download/{task_id}/source`
下载翻译后的LaTeX源码(zip压缩包)

**响应:** ZIP文件流

#### `GET /download/{task_id}/logs`
下载编译日志

**响应:** 日志文件

#### `GET /download/{task_id}/terminology`
下载术语对照表（CSV 格式）

**响应:** CSV 文件流

**说明:** 仅在翻译时启用 `generate_terminology_table` 时可用

#### `GET /tasks`
列出所有任务(调试用)

**响应:**
```json
{
  "tasks": [
    { "task_id": "abc123...", "status": "completed", ... },
    { "task_id": "xyz789...", "status": "processing", ... }
  ],
  "total": 2
}
```

#### `DELETE /task/{task_id}`
删除任务及相关文件

**响应:**
```json
{
  "task_id": "abc123...",
  "status": "deleted",
  "message": "Task deleted successfully"
}
```

### 用户认证与设置端点

#### `GET /api/settings`
获取当前登录用户的系统设置（需 JWT 认证）

**Headers:** `Authorization: Bearer <jwt_token>`

**响应:**
```json
{
  "default_source_language": "en",
  "default_target_language": "zh",
  "translation_mode": "full",
  "compile_strategy": "auto",
  "translation_model": "gpt-4.1-mini",
  "enable_verification": true,
  "generate_glossary": true,
  "use_author_api": true
}
```

#### `PUT /api/settings`
更新当前登录用户的系统设置（需 JWT 认证）

**Headers:** `Authorization: Bearer <jwt_token>`

#### `GET /api/history`
获取当前登录用户的翻译历史（需 JWT 认证，支持分页）

**Headers:** `Authorization: Bearer <jwt_token>`

**Query 参数:** `?page=1&page_size=10`

#### `GET /api/history/{task_id}`
获取翻译任务详情（需 JWT 认证）

#### `DELETE /api/history/{task_id}`
删除单条翻译历史（需 JWT 认证，支持取消处理中任务）

#### `DELETE /api/history`
批量删除翻译历史（需 JWT 认证，Body 传入 task_id 列表）

## 📝 使用示例

### 示例1: arXiv论文翻译(完整流程)

```bash
# 1. 下载arXiv论文
curl -X POST http://localhost:8000/arxiv \
  -H "Content-Type: application/json" \
  -d '{"arxiv_id": "2508.18791"}'
  
# 响应: {"task_id": "abc123...", ...}

# 2. 启动翻译
curl -X POST http://localhost:8000/translate/abc123 \
  -H "Content-Type: application/json" \
  -d '{"target_lang": "zh"}'

# 3. 查询进度(轮询)
curl http://localhost:8000/task/abc123

# 4. 下载PDF
curl -O -J http://localhost:8000/download/abc123/pdf
```

### 示例2: 上传本地文件翻译

```bash
# 1. 上传zip文件
curl -X POST http://localhost:8000/upload \
  -F "file=@my_paper.zip"
  
# 响应: {"task_id": "xyz789...", ...}

# 2. 启动翻译
curl -X POST http://localhost:8000/translate/xyz789 \
  -H "Content-Type: application/json" \
  -d '{"target_lang": "en"}'

# 3 查询状态
curl http://localhost:8000/task/xyz789

# 4. 下载源码
curl -O -J http://localhost:8000/download/xyz789/source
```

### 示例3: Python脚本

```python
import requests
import time

BASE_URL = "http://localhost:8000"

# 下载arXiv论文
response = requests.post(
    f"{BASE_URL}/arxiv",
    json={"arxiv_id": "2508.18791"}
)
task_id = response.json()["task_id"]

# 启动翻译
requests.post(
    f"{BASE_URL}/translate/{task_id}",
    json={"target_lang": "zh"}
)

# 轮询状态
while True:
    status = requests.get(f"{BASE_URL}/task/{task_id}").json()
    print(f"进度: {status['progress']}% - {status['stage']}")
    
    if status["status"] in ["completed", "completed_with_warnings"]:
        print("✅ 翻译完成!")
        break
    elif status["status"].startswith("failed"):
        print(f"❌ 失败: {status['error']}")
        break
    
    time.sleep(5)

# 下载PDF
with open(f"{task_id}.pdf", "wb") as f:
    f.write(requests.get(f"{BASE_URL}/download/{task_id}/pdf").content)
```

## 📁 项目结构

```
backend/
├── app/
│   ├── main.py                    # FastAPI应用入口
│   ├── core/
│   │   ├── config.py              # 配置管理
│   │   ├── auth.py                # JWT 认证依赖（可选认证）
│   │   ├── supabase_client.py     # 认证兼容层（迁移期保留）
│   │   └── enums.py               # 枚举定义(TaskStatus等)
│   ├── models/                    # 数据模型
│   │   └── config_models.py       # 高级配置模型
│   ├── api/
│   │   └── routes/
│   │       ├── arxiv.py           # arXiv下载端点（含可选JWT）
│   │       ├── upload.py          # 文件上传端点（含可选JWT）
│   │       ├── translate.py       # 翻译端点（支持高级配置）
│   │       ├── task.py            # 任务状态端点
│   │       ├── download.py        # 下载端点（包含术语表）
│   │       ├── settings.py        # 用户设置 CRUD（需JWT）
│   │       └── history.py         # 翻译历史查询/删除（需JWT）
│   └── services/
│       ├── task_manager.py        # 任务管理器（本地数据库持久化）
│       ├── latex_validator.py     # LaTeX目录校验器
│       ├── agents/                # 代理系统
│       │   ├── coordinator_agent.py
│       │   ├── parser_agent.py
│       │   ├── translator_agent.py
│       │   ├── generator_agent.py
│       │   └── validator_agent.py
│       └── latex/                 # LaTeX处理
│           ├── parser.py          # AST解析器
│           ├── compiler.py        # 智能编译器(pdflatex/xelatex)
│           ├── utils.py           # 工具函数(arXiv下载等)
│           ├── prompts.py         # LLM提示词
│           └── reconstruct.py     # 代码重构器
├── data/                          # 数据目录
│   ├── uploads/                   # 上传文件（按 task_id 隔离）
│   ├── outputs/                   # 翻译输出（按 task_id 隔离）
│   └── terms/                     # 术语词典（按 task_id 隔离）
├── requirements.txt               # 依赖列表
├── start.bat                      # Windows启动脚本
├── start.sh                       # Linux/Mac启动脚本
└── README.md                      # 本文档  
```

## ⚙️ 配置说明

### 环境变量

在启动脚本或系统环境中设置:

```bash
# LLM API配置
export LLM_API_KEY="your-api-key"
export LLM_BASE_URL="https://aicanapi.com/v1/chat/completions"
export LLM_MODEL="gpt-4.1-mini"
export LLM_TIMEOUT="60"

# Local Auth / MySQL（本地启动必需）
export DATABASE_URL="mysql://root:password@host.docker.internal:3306/latextrans"
export AUTH_PROVIDER_MODE="niutrans_local"
export AUTH_JWT_KEYS="v1:change-me-local-dev-secret"
export AUTH_JWT_ISSUER="latextrans-local"
export AUTH_JWT_AUDIENCE="latextrans-api"
export AUTH_ACCESS_TOKEN_TTL_SECONDS="28800"
export NIUTRANS_AUTH_URL="https://niutrans.com/niutrans-auth/auth/login"
export NIUTRANS_LOGIN_URL="https://niutrans.com/login?active=0"
export NIUTRANS_REGISTER_URL="https://niutrans.com/login?active=3"
export NIUTRANS_ACCOUNT_URL="https://niutrans.com/login?active=0"
export ENCRYPTION_KEY="your-32-byte-key"        # 用于加密用户 API Key
export ENABLE_SUPABASE_IMPORT_READONLY="false"  # 仅迁移期只读导入开关，可保持关闭

# LaTeX工具路径(可选,如果不在PATH中)
export LATEX_BIN_DIR="/usr/local/texlive/2024/bin/x86_64-linux"

# 数据目录(可选)
export DATA_DIR="/path/to/data"
```

> **注意**: 本地启动与验证不需要 Supabase runtime credentials。只需保证 MySQL 与本地认证变量可用即可。

### 配置文件

编辑 `backend/app/core/config.py`:

```python
class Settings:
    # API配置
    api_key: str = "sk-..."
    base_url: str = "https://..."
    model: str = "gpt-4.1-mini"
    
    # 路径配置
    uploads_dir: Path = Path("data/uploads")
    outputs_dir: Path = Path("data/outputs")
    
    # 编译配置
    latex_timeout: int = 300  # 超时时间(秒)
```

## 🔧 故障排除

### 1. 启动失败: `ModuleNotFoundError`

**问题:** 无法导入 `backend.app.main`

**解决:**
```bash
# 确保从项目根目录启动,不是backend/目录
cd /path/to/LaTexTrans
python -m uvicorn backend.app.main:app --reload
```

### 2. arXiv下载失败

**问题:** `tar: command not found` (Windows)

**解决:**
- 安装 Git Bash 并添加到PATH
- 或使用 WSL (Windows Subsystem for Linux)
- 或手动安装 GNU tar for Windows

### 3. 编译失败: `pdflatex not found`

**问题:** LaTeX未安装或不在PATH中

**解决:**
```bash
# 检查LaTeX
which pdflatex
which xelatex

# 如果未找到,设置环境变量
export LATEX_BIN_DIR="/path/to/texlive/bin"
```

### 4. 翻译卡住在某个进度

**问题:** LLM API超时或限流

**解决:**
- 检查API key是否有效
- 增加 `LLM_TIMEOUT` 值
- 查看 `data/outputs/{task_id}/translation.log`

### 5. 内存不足

**问题:** 处理大型论文时OOM

**解决:**
- 增加系统内存
- 减小并发任务数
- 考虑添加任务队列(如Celery)

### 6. 端口被占用

**问题:** `Address already in use: 8000`

**解决:**
```bash
# 使用其他端口
python -m uvicorn backend.app.main:app --port 9001
```

### 7. CORS错误(前端调用)

**问题:** `Access-Control-Allow-Origin` 错误

**解决:**
编辑 `backend/app/main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # 添加你的前端URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 8. 文件上传大小限制

**问题:** `413 Request Entity Too Large`

**解决:**
编辑 `backend/app/main.py`:
```python
app = FastAPI(
    max_request_size=100 * 1024 * 1024  # 100MB
)
```

## 📚 更多资源

- **API文档**: http://localhost:8000/docs (启动服务后访问)
- **前端文档**: `frontend/README.md`
- **OpenSpec 变更记录**: `openspec/changes/archive/`
- **CLI版本**: `python prototype_system/main.py --help`

## 🧪 测试

运行综合测试套件:

```bash
# 确保后端正在运行
python backend/test_api_comprehensive.py
```

测试覆盖:
- ✅ 错误处理(无效ID、文件缺失)
- ✅ 编译器智能机制
- ✅ 错误对比与选择
- ✅ CLI兼容性

## 📜 许可

见项目根目录 `LICENSE` 文件

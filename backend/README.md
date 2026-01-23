# LaTeXTrans Backend

Web MVP 后端 API 服务 - 最小可测试版本

## 快速开始

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

**注意**: 如果遇到 `tiktoken` 编译错误,这是正常的,该依赖已被注释掉(MVP 不需要)。

### 2. 启动服务器

**Linux/Mac:**
```bash
chmod +x start.sh
./start.sh
```

**Windows:**
```powershell
.\start.ps1
```

**或直接使用 uvicorn:**
```bash
cd ..  # 回到项目根目录
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. 访问 API

服务启动后访问:
- **API 文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health
- **根路径**: http://localhost:8000/

## API 端点

### ✅ 已实现 (MVP 版本)

#### GET /health
健康检查端点

**响应:**
```json
{
  "status": "healthy",
  "app": "LaTeXTrans Backend",
  "version": "0.1.0",
  "llm_model": "gpt-4.1-mini"
}
```

#### POST /api/arxiv
下载 arXiv 论文源码

**请求:**
```json
{
  "arxiv_id": "2508.18791"
}
```

**响应:**
```json
{
  "task_id": "uuid-string",
  "arxiv_id": "2508.18791",
  "status": "success",
  "message": "arXiv paper 2508.18791 downloaded successfully",
  "source_path": "/path/to/data/uploads/{task_id}/2508.18791"
}
```

#### GET /api/arxiv/validate/{arxiv_id}
验证 arXiv ID 格式

**响应:**
```json
{
  "arxiv_id": "2508.18791",
  "is_valid": true,
  "message": "Valid arXiv ID"
}
```

### ⏳ 待实现 (后续版本)

以下端点将在完整版本中实现:
- `POST /api/upload` - 文件上传
- `POST /api/translate/{task_id}` - 触发翻译
- `GET /api/task/{task_id}` - 查询任务状态
- `GET /api/download/{task_id}/pdf` - 下载 PDF
- `GET /api/download/{task_id}/source` - 下载源码

## 项目结构

```
backend/
├── app/
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py           # ✅ 配置管理
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       └── arxiv.py        # ✅ arXiv 下载路由
│   ├── services/
│   │   ├── __init__.py
│   │   ├── task_manager.py     # ✅ 任务管理器
│   │   └── latex/
│   │       ├── __init__.py
│   │       ├── compiler.py     # ✅ 智能编译器
│   │       └── utils.py        # ✅ 简化工具函数
│   ├── __init__.py
│   └── main.py                 # ✅ FastAPI 应用
├── requirements.txt            # ✅ 依赖列表
├── start.sh                    # ✅ Linux/Mac 启动脚本
└── start.ps1                   # ✅ Windows 启动脚本
```

## 配置

配置文件位于 `app/core/config.py`,支持以下环境变量:

- `LLM_API_KEY`: LLM API 密钥 (默认: sk-SVd...)
- `LLM_BASE_URL`: API 基础 URL (默认: https://aicanapi.com/v1)
- `LLM_MODEL`: 模型名称 (默认: gpt-4.1-mini)
- `LLM_TIMEOUT`: 请求超时 (默认: 60秒)

## 测试

### 使用 curl

**健康检查:**
```bash
curl http://localhost:8000/health
```

**下载 arXiv 论文:**
```bash
curl -X POST http://localhost:8000/api/arxiv \
  -H "Content-Type: application/json" \
  -d '{"arxiv_id": "2508.18791"}'
```

**验证 arXiv ID:**
```bash
curl http://localhost:8000/api/arxiv/validate/2508.18791
```

### 使用 Python

```python
import requests

# 健康检查
response = requests.get("http://localhost:8000/health")
print(response.json())

# 下载 arXiv 论文
response = requests.post(
    "http://localhost:8000/api/arxiv",
    json={"arxiv_id": "2508.18791"}
)
print(response.json())
```

## 数据存储

下载的文件存储在:
```
data/
├── uploads/
│   └── {task_id}/
│       └── {arxiv_id}/
│           ├── main.tex
│           ├── ...
│           └── {arxiv_id}.pdf
├── outputs/      # 翻译输出 (待实现)
└── terms/        # 术语词典 (待实现)
```

## 已知限制 (MVP 版本)

1. **无翻译功能**: 仅支持下载,翻译功能待后续实现
2. **无进度追踪**: 下载是同步的,没有实时进度更新
3. **无文件上传**: 仅支持 arXiv 下载
4. **内存存储**: 任务状态存储在内存中,重启丢失
5. **无认证**: 没有用户认证

## 下一步

完整功能实施需要:
1. LaTeX 解析器改编
2. 翻译代理系统改编
3. 文件上传端点
4. 翻译任务端点
5. 下载端点
6. 进度追踪

详见 `openspec/changes/add-web-mvp-platform/` 中的实施计划文档。

## 故障排除

### 依赖安装失败

如果遇到编译错误:
1. `tiktoken` 需要 Rust - 已在 MVP 中禁用
2. 确保 Python 版本 >= 3.10

### 端口被占用

修改 `app/core/config.py` 中的 `port` 设置,或使用:
```bash
python -m uvicorn backend.app.main:app --port 8001
```

### 无法导入模块

确保从项目根目录运行,而不是 `backend/` 目录。

## 开发日志

查看 `openspec/changes/add-web-mvp-platform/PROGRESS.md` 了解详细的开发进度。

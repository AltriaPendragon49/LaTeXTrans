# Implementation Tasks

## 1. Code Audit and Refactoring Preparation
- [ ] 1.1 Review `prototype_system/src/agents/coordinator_agent.py` to understand workflow orchestration
- [ ] 1.2 Review `prototype_system/src/formats/latex/parser.py` and `compile.py` for AST parsing and compilation logic
- [ ] 1.3 Review `prototype_system/src/formats/latex/utils.py` for arXiv download utilities
- [ ] 1.4 Document reusable components and required adaptations (remove Streamlit dependencies)
- [ ] 1.5 Create reuse mapping document listing files to copy/adapt

## 2. Project Structure Initialization (Backend Only)
- [ ] 2.1 Create `backend/app/` directory structure (`core/`, `api/routes/`, `services/`)
- [ ] 2.2 Create `data/` directory structure (`uploads/`, `outputs/`, `terms/`)
- [ ] 2.3 Create `docker/` directory for future containerization
- [ ] 2.4 Initialize `backend/requirements.txt` with FastAPI dependencies

**Note**: Frontend initialization (React/Vite setup) is handled separately in the `add-web-mvp-frontend` change.

## 3. Backend Core Services
- [ ] 3.1 Adapt LaTeX parser from prototype to `backend/app/services/latex/parser.py`
  - Remove `st.progress()` and `st.text()` dependencies
  - Add progress callback mechanism for web integration
- [ ] 3.2 Adapt LaTeX utilities to `backend/app/services/latex/utils.py`
  - Copy `batch_download_arxiv_tex()` and related functions
  - Adapt file paths for web environment
- [ ] 3.3 Implement intelligent LaTeX compiler with fallback (`backend/app/services/latex/compiler.py`)
  - Create `compile_with_fallback()` function that tries pdflatex first, then xelatex
  - Implement `.log` file parser to count errors (match patterns: `! LaTeX Error`, `! Undefined control sequence`, `! Missing`)
  - Compare error counts and select PDF with fewer errors
  - Return best PDF or raise exception if both fail
  - Support MiKTeX auto-install for missing packages
- [ ] 3.4 Adapt agent system to `backend/app/services/agents/`
  - Copy `coordinator_agent.py`, `parser_agent.py`, `translator_agent.py`, etc.
  - Replace Streamlit logging with structured logging (Python `logging` module)
  - Update `generator_agent.py` to use new `compile_with_fallback()` function
- [ ] 3.5 Create task manager service (`backend/app/services/task_manager.py`)
  - In-memory task status tracking
  - Progress update mechanism (0-100%)
  - Task state management (pending → processing → completed/failed)


## 4. Backend API Implementation
- [ ] 4.1 Create FastAPI application skeleton (`backend/app/main.py`)
  - Initialize FastAPI with CORS middleware
  - Add `/health` endpoint
- [ ] 4.2 Implement `POST /upload` endpoint (`backend/app/api/routes/upload.py`)
  - Accept `.zip` or `.tex` file uploads
  - Generate unique task ID
  - Save files to `data/uploads/{task_id}/`
  - Extract compressed files if `.zip`
  - Return task ID and status
- [ ] 4.3 Implement `POST /arxiv` endpoint (`backend/app/api/routes/arxiv.py`)
  - Accept arXiv ID in request body
  - Call `batch_download_arxiv_tex()` from adapted utils
  - Save to `data/uploads/{task_id}/`
  - Return task ID and status
- [ ] 4.4 Implement `POST /translate/{task_id}` endpoint (`backend/app/api/routes/translate.py`)
  - Validate task ID exists
  - Load translation configuration
  - Use FastAPI `BackgroundTasks` to run translation asynchronously
  - Call `CoordinatorAgent.workflow_latextrans()` in background
  - Update task status via TaskManager
- [ ] 4.5 Implement `GET /task/{task_id}` endpoint (`backend/app/api/routes/task.py`)
  - Query task status from TaskManager
  - Return {status, progress, message, error?}
- [ ] 4.6 Implement `GET /download/{task_id}/pdf` endpoint (`backend/app/api/routes/download.py`)
  - Locate translated PDF in `data/outputs/`
  - Return file as download attachment
- [ ] 4.7 Implement `GET /download/{task_id}/source` endpoint
  - Package translated `.tex` files as `.zip`
  - Return archive as download attachment

## 5. Integration and Configuration
- [ ] 5.1 Create backend configuration module (`backend/app/core/config.py`)
  - Load settings from environment variables or `config/default. toml`
  - Configure LLM API with specific parameters:
    * `api_key`: "sk-SVd4dIKfuIwhQ9kUlgCr9ZMpoIWp7PEzZxpVStjSRqeqNBLu" (load from env var `LLM_API_KEY` if available)
    * `base_url`: "https://aicanapi.com/v1"
    * `model`: "gpt-4.1-mini" (or as specified)
    * `timeout`: 60 seconds
  - Storage paths configuration
  - Task status enum definitions (pending, processing, completed, completed_with_warnings, failed_compilation, failed)
- [ ] 5.2 Wire up all API routes in `backend/app/main.py`
  - Import and include routers for upload, arxiv, translate, task, download
- [ ] 5.3 Configure CORS to allow frontend origin (http://localhost:5173)
- [ ] 5.4 配置后端启动脚本环境变量和路径

## 6. Backend API Testing
- [ ] 6.1 Test `POST /upload` endpoint with sample `.tex` file via curl/Postman
- [ ] 6.2 Test `POST /arxiv` endpoint with valid arXiv ID (e.g., `2508.18791`)
- [ ] 6.3 Test `POST /translate/{task_id}` triggers background translation
- [ ] 6.4 Test `GET /task/{task_id}` returns correct status and progress
- [ ] 6.5 Test `GET /download/{task_id}/pdf` returns valid PDF file
- [ ] 6.6 Test `GET /download/{task_id}/source` returns valid .zip archive
- [ ] 6.7 Test error handling: Invalid task ID, missing files, translation errors
- [ ] 6.8 Test compiler fallback: File that fails with pdflatex but succeeds with xelatex
- [ ] 6.9 Test compiler error comparison: File with intentional errors
- [ ] 6.10 Verify CLI still works: `python prototype_system/main.py --arxiv 2508.18791`

**Note**: End-to-end integration testing with frontend UI is handled in the `add-web-mvp-frontend` change.

## 7. Documentation
- [ ] 7.1 Create `backend/README.md` with setup and run instructions
- [ ] 7.2 Document API endpoints (OpenAPI/Swagger auto-generated via FastAPI)
- [ ] 7.3 Create API testing guide (curl examples, Postman collection)
- [ ] 7.4 Create troubleshooting guide for common backend issues

**Note**: Frontend documentation is handled in the `add-web-mvp-frontend` change.

## 8. Deployment Preparation
- [ ] 8.1 Create `backend/Dockerfile` for containerization (deferred to Phase 4)
- [ ] 8.2 Create startup script for backend:
  - `backend/start.sh` (setup environment, run uvicorn)
- [ ] 8.3 Document backend environment setup requirements

## Dependencies and Sequencing

**Critical Path**: Tasks must be completed in order within each section.
**Blockers**: 
- Task 3.x must complete before 4.x (API needs services)
- Task 4.x must complete before 6.x (testing needs endpoints)
- Task 1.x must complete before 3.x (need to understand what to adapt)

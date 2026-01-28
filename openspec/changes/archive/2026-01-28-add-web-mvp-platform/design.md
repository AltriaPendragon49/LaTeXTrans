# Design Document: Web-Based MVP Platform

## Context

### Background
The LaTeXTrans project currently exists as a CLI prototype (`prototype_system/`) that demonstrates core LaTeX translation capabilities using a multi-agent architecture. However, it:
- Requires Python environment setup and command-line proficiency
- Lacks real-time feedback during translation (relies on Streamlit in some modules)
- Has no web-accessible interface for broader usability

### Constraints
- **AST Parsing**: Must continue using `pylatexenc` for LaTeX structure handling (no regex)
- **Python Environment**: Backend requires Python 3.10+ with necessary dependencies
- **Docker Isolation**: LaTeX compilation must occur in Docker with MiKTeX
- **Backward Compatibility**: Existing CLI prototype must remain functional
- **Timeline**: 2-week MVP delivery window

### Stakeholders
- End Users: Researchers and students needing LaTeX translation
- Development Team: Building toward full RAG + Multi-Agent system (Phases 2-5)
- Thesis Committee: Requires demonstrable web platform with evaluation metrics

## Goals / Non-Goals

### Goals
1. **End-to-End Web Workflow**: Upload → Translate → Download via browser
2. **Real-Time Progress Feedback**: Users see translation stages and completion percentage
3. **arXiv Integration**: Support direct translation from arXiv paper IDs
4. **Code Reusability**: Adapt (not rewrite) proven prototype logic
5. **Foundation for Future**: Establish architecture for RAG/Agent enhancements (Phases 2-3)

### Non-Goals
1. ❌ User authentication or multi-tenancy (single-user local deployment)
2. ❌ RAG-based terminology retrieval (deferred to Phase 2)
3. ❌ LangChain agent orchestration (deferred to Phase 3)
4. ❌ Advanced UI features: dual-pane preview, syntax highlighting (deferred to Phase 4)
5. ❌ Production deployment infrastructure (MVP is local-first)
6. ❌ Database persistence (use in-memory task tracking for MVP)

## Decisions

### Decision 1: FastAPI over Flask/Django
**Choice**: FastAPI  
**Rationale**:
- Native async/await support for background task handling
- Automatic OpenAPI documentation (valuable for testing and future integration)
- Type hints improve code maintainability
- Better performance for I/O-bound operations (file uploads, arXiv downloads)
- Modern Python ecosystem alignment (Python 3.10+)

**Alternatives Considered**:
- Flask: Simpler but lacks native async; requires extensions for OpenAPI
- Django: Overkill for MVP scope; heavier framework with ORM we don't need

### Decision 2: React + Vite over vanilla HTML or Next.js
**Choice**: React with Vite tooling  
**Rationale**:
- React component model matches UI requirements (upload, progress, download as isolated components)
- Vite provides fast hot-reload for rapid development
- TailwindCSS integration is straightforward with Vite
- Smaller learning curve than Next.js for team
- No SSR needed for local MVP

**Alternatives Considered**:
- Vanilla HTML/JS: Harder to manage state for polling and progress updates
- Next.js: Overkill for client-only app; SSR not needed for local deployment

### Decision 3: In-Memory Task State over Database
**Choice**: Python dictionary-based TaskManager  
**Rationale**:
- MVP assumes single-user, short sessions
- Eliminates setup complexity (no PostgreSQL/Redis dependency for MVP)
- Faster development iteration
- Easy migration to Redis/DB in Phase 4 when concurrency becomes a priority

**Trade-off**: Task state lost on server restart (acceptable for MVP)

### Decision 4: File-Based Storage over S3/Cloud
**Choice**: Local filesystem (`data/uploads/`, `data/outputs/`)  
**Rationale**:
- No cloud dependencies or costs
- Simpler error handling and debugging
- Meets local deployment requirement
- Easy migration path to object storage later

**Trade-off**: No distributed access (acceptable for single-machine MVP)

### Decision 5: Adapt Prototype Code, Don't Rewrite
**Choice**: Copy and modify existing `coordinator_agent.py`, `parser.py`, `utils.py`  
**Rationale**:
- Proven logic reduces risk of introducing LaTeX parsing bugs
- 70% of code can be reused with Streamlit removal
- Faster than rebuilding from scratch
- Maintains AST parsing compliance (`pylatexenc` usage)

**Approach**:
- Remove: `st.progress()`, `st.text()`, `st.spinner()` calls
- Add: Progress callbacks (`on_progress(stage, percent)`) consumed by TaskManager
- Preserve: All AST logic, compiler logic, agent orchestration

### Decision 6: Polling over WebSockets for Progress
**Choice**: Frontend polls `GET /task/{task_id}` every 2 seconds  
**Rationale**:
- Simpler implementation (no WebSocket server setup)
- Adequate UX for 2-10 minute translations (WebSocket overkill)
- Easier debugging with standard HTTP requests
- WebSocket upgrade deferred to Phase 4 (real-time logs)

**Trade-off**: Slightly higher latency (~2s vs instant), acceptable for MVP

### Decision 7: Monorepo Structure
**Choice**: Single repository with `backend/`, `frontend/`, `prototype_system/` directories  
**Rationale**:
- Easier cross-referencing during prototype adaptation
- Simplified dependency management for thesis deliverable
- Aligns with OpenSpec workflow (single project.md)

**File Structure**:
```
LaTeXTrans/
├── backend/        # FastAPI + adapted prototype logic
├── frontend/       # React + Vite
├── prototype_system/  # Original CLI (preserved as reference)
├── data/           # Runtime storage (gitignored)
├── openspec/       # This proposal and future specs
└── docker/         # Future: MiKTeX container
```

## Architecture Overview

### Request Flow
```
User Browser
    ↓ (Upload .zip or arXiv ID)
React Frontend (localhost:5173)
    ↓ (POST /upload or /arxiv → task_id)
    ↓ (POST /translate/{task_id})
FastAPI Backend (localhost:8000)
    ↓ (Background Task)
CoordinatorAgent (adapted from prototype)
    ├─ ParserAgent → AST extraction (pylatexenc)
    ├─ TranslatorAgent → LLM translation (Gemini)
    └─ GeneratorAgent → xelatex compilation (future: Docker)
    ↓ (Writes to data/outputs/)
TaskManager (updates {task_id: {status, progress}})
    ↑ (Polled by frontend via GET /task/{task_id})
React Frontend
    ↓ (Downloads via GET /download/{task_id}/pdf)
User Browser (receives translated PDF)
```

### Key Components

**Backend Services**:
- `TaskManager`: In-memory state store for task status/progress
- `LaTeXParser`: Adapted from `prototype_system/src/formats/latex/parser.py`
- `ArxivUtils`: Adapted from `prototype_system/src/formats/latex/utils.py`
- `CoordinatorAgent`: Adapted from `prototype_system/src/agents/coordinator_agent.py`

**API Routes**:
- `POST /upload` → Receives file, returns task_id
- `POST /arxiv` → Receives arXiv ID, downloads source, returns task_id
- `POST /translate/{task_id}` → Triggers background translation
- `GET /task/{task_id}` → Returns {status, progress, message}
- `GET /download/{task_id}/pdf` → Streams PDF file
- `GET /download/{task_id}/source` → Streams zipped source

**Frontend Components**:
- `FileUpload.jsx`: Drag-and-drop + file selection
- `ArxivInput.jsx`: arXiv ID input with validation
- `ProgressTracker.jsx`: Polling + progress bar + status display
- `DownloadButton.jsx`: Conditional rendering on completion
- `App.jsx`: Layout orchestration with tab switcher

## Data Model

### Task Object (in-memory)
```python
{
    "task_id": "uuid-string",
    "status": "pending" | "processing" | "completed" | "completed_with_warnings" | "failed_compilation" | "failed",
    "progress": 0-100,  # percentage
    "stage": "parsing" | "translating" | "compiling" | "done" | "compilation_failed",
    "message": "Current operation description",
    "error": null | "Error message",
    "warnings": null | "Compilation warning summary",
    "source_available": true | false,  # LaTeX source can be downloaded
    "created_at": "ISO timestamp",
    "completed_at": null | "ISO timestamp",
    "source_type": "upload" | "arxiv",
    "source_path": "data/uploads/{task_id}/",
    "output_path": "data/outputs/ch_{project_name}/"
}
```

### LLM API Configuration
The backend SHALL use the following LLM API configuration (adapted from prototype's `config/default.toml`):

```python
LLM_CONFIG = {
    "api_key": "sk-SVd4dIKfuIwhQ9kUlgCr9ZMpoIWp7PEzZxpVStjSRqeqNBLu",
    "base_url": "https://aicanapi.com/v1/chat/completions",
    "model": "gpt-4.1-mini",  # or as specified in config
    "timeout": 60  # seconds per request
}
```

**Note**: API key should be loaded from environment variable `LLM_API_KEY` or config file, not hardcoded in source code.

### File Storage Layout
```
data/
├── uploads/
│   └── {task_id}/
│       ├── original.zip (if uploaded)
│       └── extracted/
│           └── main.tex
├── outputs/
│   └── ch_{project_name}/
│       ├── translated.tex
│       ├── translated.pdf
│       └── ... (supporting files)
└── terms/
    └── *.csv (terminology glossaries, unused in MVP)
```

## Risks / Trade-offs

### Risk 1: Translation Timeouts
**Issue**: Long papers (>50 pages) may take >10 minutes  
**Mitigation**:
- Use FastAPI `BackgroundTasks` to avoid HTTP timeout
- Frontend shows cancel button (future: POST /task/{task_id}/cancel)
- Set reasonable timeout in LLM calls (60s per chunk)

### Risk 2: Latex Compilation Failures
**Issue**: MiKTeX Docker not yet implemented in MVP  
**Mitigation**:
- Phase 1: Run xelatex on host system (requires local MiKTeX installation)
- Document Docker setup as post-MVP enhancement
- Include compilation error logs in task error field

### Risk 3: Concurrent User Requests
**Issue**: In-memory TaskManager not thread-safe  
**Mitigation**:
- Use Python `threading.Lock()` for task dictionary updates
- Document single-user limitation in README
- Plan Redis migration for Phase 4

### Risk 4: Large File Uploads
**Issue**: 100MB+ `.zip` files could exhaust memory  
**Mitigation**:
- FastAPI streaming upload (`UploadFile`)
- Set max upload size limit (50MB for MVP)
- Validate file size before processing

### Risk 5: Streamlit Dependency Removal
**Issue**: Prototype code may fail when removing UI calls  
**Mitigation**:
- Thorough code audit (Task 1.x) before adaptation
- Replace logging calls with Python `logging` module
- Add unit tests for core functions (parser, translator)

## Migration Plan

### Phase 0 → Phase 1 (This Change)
1. Create new `backend/` and `frontend/` directories (non-destructive)
2. Copy prototype code to `backend/app/services/`
3. Adapt copied code (original prototype remains untouched)
4. Build web UI and API layer
5. Run parallel testing: CLI vs Web workflow

### Rollback Strategy
- Delete `backend/` and `frontend/` directories
- Prototype system remains fully functional
- No migration of existing users (none exist yet)

### Testing Before Merge
- [ ] CLI workflow unaffected: `python prototype_system/main.py --arxiv 2508.18791` succeeds
- [ ] Web workflow functional: Upload → Translate → Download succeeds
- [ ] Compare outputs: Same arXiv paper translated via CLI and Web produces identical PDF

## Open Questions

1. **Q**: Should we support batch uploads (multiple papers at once)?  
   **A**: No for MVP. Single task per request. Batch feature deferred to Phase 4.

2. **Q**: Do we need user sessions or can tasks be globally accessible by ID?  
   **A**: Global task IDs (UUID) are sufficient for single-user MVP. Session isolation deferred.

3. **Q**: Should frontend build be served by FastAPI or run separately?  
   **A**: Run separately in development (Vite dev server). Production build served by FastAPI later.

4. **Q**: How to handle missing LaTeX packages during compilation?  
   **A**: For MVP, assume MiKTeX on host with auto-install enabled. Docker isolates this in Phase 3.

5. **Q**: Should we log all API requests for debugging?  
   **A**: Yes. Use FastAPI middleware to log requests/responses. Store in `backend/logs/`.

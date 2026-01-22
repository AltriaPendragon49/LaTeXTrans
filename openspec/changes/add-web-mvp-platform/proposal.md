# Change: Add Web-Based MVP Translation Platform

## Why

The current prototype system (`prototype_system/`) is a CLI-only tool that requires technical knowledge to operate. To make LaTeX translation accessible to a broader audience and meet thesis requirements, we need a web-based platform that:

- Allows users to upload `.zip` files or provide arXiv IDs through a browser interface
- Provides real-time translation progress feedback
- Enables easy download of translated PDFs and source files
- Maintains backward compatibility with the existing CLI workflow

This MVP focuses on establishing the full end-to-end pipeline (front-end to back-end) without advanced RAG or multi-modal agent features, following the "Skeleton First" architectural principle.

## What Changes

- **Frontend**: React-based web application with file upload, progress tracking, and download capabilities
- **Backend**: FastAPI service exposing RESTful APIs for upload, translation, task status, and download
- **Project Structure**: New `backend/` and `frontend/` directories alongside `prototype_system/`
- **Code Reuse**: Adapt existing LaTeX parser, coordinator agent, and arXiv utilities from prototype
- **Storage**: Local file-based storage for uploads and outputs (`data/` directory)

**Breaking Changes**: None - this is additive. The existing CLI prototype remains functional.

## Impact

### Affected Specs
- **NEW**: `web-api` - RESTful API endpoints for translation workflow
- **NEW**: `web-ui` - React frontend for user interaction
- **NEW**: `file-management` - Upload, storage, and download handling
- **MODIFIED**: `latex-translation-core` - Refactor to support both CLI and web interfaces

### Affected Code
- New directories: `backend/`, `frontend/`, `data/`
- Reused from prototype: 
  - `prototype_system/src/agents/coordinator_agent.py`
  - `prototype_system/src/formats/latex/parser.py`
  - `prototype_system/src/formats/latex/utils.py`
  - `prototype_system/main.py` (arXiv logic)
- Preserved: `prototype_system/` remains unchanged as reference implementation

## Timeline
2 weeks (Phase 1 of 5-phase roadmap)

## Validation Criteria
- ✅ Web UI accessible at http://localhost:5173
- ✅ File upload (`.zip` / `.tex`) creates task and triggers translation
- ✅ arXiv ID input downloads source and translates
- ✅ Progress updates visible in frontend (0-100%)
- ✅ Translated PDF downloadable and valid
- ✅ CLI workflow (`python main.py --arxiv`) still functional

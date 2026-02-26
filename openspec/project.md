# Project Context

## Purpose
LaTeXTrans-Pro is a LaTeX paper translation system based on Retrieval-Augmented Generation (RAG) and Multi-Agent collaboration. It aims to solve the issues of terminology inconsistency, context loss, and compilation errors when translating LaTeX papers, ensuring that the translated document maintains its format and can be correctly compiled into a PDF.

## Tech Stack
- **Backend:** Python 3.10+, FastAPI, LangChain
- **Frontend:** React 18+, TailwindCSS, Vite
- **Database:** ChromaDB (Vector database for terms), Redis (Task queue)
- **Embedding:** bge-m3
- **Retrieval:** Hybrid (Semantic + BM25) with Cross-Encoder re-ranking
- **Multi-modal:** Gemini-Vision (for image content understanding)
- **LLM:** Gemini via LangChain (fallback to GPT)
- **LaTeX Engine:** MiKTeX (via Docker, with 'install on the fly')

## Project Conventions

### Code Style
- Follow Python PEP 8 for backend development.
- Use Conventional Commits (e.g., `feat: add rag retriever`, `fix: parser logic`).
- All new features should include unit tests.

### Architecture Patterns
- **Skeleton First:** Prioritize building the full end-to-end pipeline before filling in complex sub-module logic.
- **Agent Orchestration:** Use LangChain Agents (Translator, Compiler, CiteTool, ImageTool) to handle specialized tasks.
- **RESTful API:** Communication between React frontend and FastAPI backend.
- **Target Language Persistence:** A flawed translated PDF is better than reverting to the English original. For structural restoration fallbacks, always prefer keeping the target language text (even with minor tag/math malformations) over nuclear fallbacks to source text.

### Testing Strategy
- AST parsing tests are mandatory to ensure LaTeX structure integrity.
- Unit tests for core services (Parser, RAG, Agents).
- Manual verification of compiled PDFs for format consistency.

### Git Workflow
- Standard branching strategy (main/dev branches).
- Mandatory commit messages following the Conventional Commits specification.

## Domain Context
The project operates in the domain of Academic Paper Translation and LaTeX Document Processing. Key concepts include:
- **AST Parsing:** Converting LaTeX source code into an Abstract Syntax Tree to extract text while preserving structure.
- **Terminology Consistency:** Ensuring technical terms (e.g., "Self-Attention") are translated consistently using domain-specific glossaries.
- **Compilation Self-Healing:** Automatically identifying and fixing LaTeX compilation errors caused by translation or missing packages.

## Important Constraints
- **AST Parser:** Must use `pylatexenc` for parsing; regex is strictly forbidden for LaTeX structure handling.
- **Docker Isolation:** LaTeX compilation must occur in a Docker-isolated environment using MiKTeX.
- **RAG-Driven:** Translation MUST use RAG-retrieved terms to avoid model hallucinations.

## External Dependencies
- **LLM APIs:** Google Gemini (primary), OpenAI GPT (fallback).
- **ArXiv API:** Used by CiteTool to fetch paper abstracts for context.
- **Docker Engine:** Required for running the LaTeX compilation environment.

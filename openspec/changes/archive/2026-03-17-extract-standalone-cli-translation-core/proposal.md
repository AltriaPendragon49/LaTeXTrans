# Proposal: Extract Standalone CLI Translation Core

## Description
Extract the mature translation kernel from the current `backend/` implementation and land it into `NiuTrans/LaTeXTrans` as a standalone CLI-first open-source tool. The resulting project preserves the prototype-style repository surface and `main.py` command flow while replacing the old prototype internals with the current production translation pipeline.

## Motivation
- The current backend translation kernel has significantly stronger structure protection, fallback routing, replay-bundle generation, and compilation diagnostics than the legacy prototype.
- The open-source deliverable should be a clean CLI tool, not a FastAPI backend stripped down after the fact.
- The existing `NiuTrans/LaTeXTrans` layout already matches the desired public-facing form factor and old-command compatibility expectations.

## Scope
- Replace prototype internals in `NiuTrans/LaTeXTrans` with the current backend translation core.
- Remove FastAPI, Supabase, queue, auth, persistence, and Streamlit dependencies from the open-source CLI surface.
- Add a local runtime/settings layer so the extracted kernel does not import `backend.app.*`.
- Keep compatibility with legacy CLI flags such as `--config`, `--model`, `--url`, `--key`, `--arxiv`, `--output`, and `--source`.

## Non-Goals
- Preserving the web backend shape or continuing to share runtime state with `backend/`.
- Shipping frontend, user-history, auth, or database-backed features in the open-source artifact.
- Moving evaluation assets into the first standalone CLI release.

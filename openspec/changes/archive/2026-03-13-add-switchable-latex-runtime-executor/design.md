## Context
LaTeX compilation entry points are centralized in `backend/app/services/latex/compiler.py` (`compile_latex` and `_compile_latex_direct`). Current implementation invokes host commands directly (`latexmk`, `pdflatex`, `xelatex`, `lualatex`) via subprocess.

## Goals / Non-Goals
- Goals:
  - Add runtime-selectable LaTeX execution (host vs docker)
  - Keep business-layer APIs unchanged
  - Keep fallback sequencing, diagnostics, and process cleanup behavior unchanged
- Non-Goals:
  - No refactor of fallback decision logic
  - No changes to compile parameter construction semantics
  - No changes to log parsing, error classification, or task status mapping

## Decisions
- Decision: Use an executor abstraction at subprocess command finalization boundary.
  - Why: This is the smallest insertion point to switch runtime without touching business flow.
- Decision: `HostLatexExecutor` passes command through unchanged.
  - Why: Preserves existing host behavior when explicitly selected.
- Decision: `DockerLatexExecutor` only wraps/normalizes command for container execution.
  - Why: Keeps compiler business logic free of direct docker command assembly.
- Decision: Select executor via env var `LATEX_RUNTIME_MODE` with default `docker`.
  - Why: Ensures a unified TeX runtime by default across environments.
- Decision: Invalid runtime values degrade to docker mode with warning.
  - Why: Keep safe baseline aligned with containerized runtime standard.

## Risks / Trade-offs
- Docker mode depends on host Docker daemon availability.
- Path mapping across host/container must preserve output directory behavior.
- Host mode is now opt-in and should be used only when explicitly needed.

## Migration Plan
1. Deploy code without setting `LATEX_RUNTIME_MODE` to use docker by default.
2. For explicit host execution, set `LATEX_RUNTIME_MODE=host`.
3. Optionally set `LATEX_DOCKER_IMAGE` per environment.
4. Validate compile output paths and diagnostics parity.

## Rollback Plan
- Immediate rollback to host path by setting `LATEX_RUNTIME_MODE=host`.
- Full rollback by reverting `backend/app/services/latex/compiler.py`.

## Open Questions
- None. This change is scoped to `compiler.py` and env-driven configuration only.

# Change: Add Runtime-Selectable LaTeX Executor Strategy

## Why
Current LaTeX compilation executes host binaries directly via subprocess, which makes it hard to guarantee a unified TeX runtime across local development, production, and CI.

We need an infrastructure-level runtime switch while preserving existing compiler behavior, fallback logic, and operational diagnostics.

## What Changes
- Introduce a minimal executor abstraction in `backend/app/services/latex/compiler.py`:
  - `LatexExecutor`
  - `HostLatexExecutor`
  - `DockerLatexExecutor`
- Limit executor responsibility to command finalization only:
  - Input: already-constructed LaTeX command (`list[str]`)
  - Output: final command for subprocess execution (`list[str]`)
- Add environment-based runtime switch:
  - `LATEX_RUNTIME_MODE=host|docker` (default: `docker`)
- Add docker image configuration:
  - `LATEX_DOCKER_IMAGE` (default: `latextrans-runtime:texlive2025`)
- Docker mode wraps command with:
  - `docker run --rm -v <workdir>:/work -w /work <image> <command...>`
- Preserve existing behavior constraints:
  - No business API signature changes
  - No engine fallback order changes
  - No compile error handling changes
  - No `_kill_process_tree` behavior changes
- Runtime selection rule:
  - Only explicit `LATEX_RUNTIME_MODE=host` uses host path
  - Unset or invalid runtime mode uses docker executor

## Impact
- Affected specs:
  - `latex-translation-core`
- Affected code:
  - `backend/app/services/latex/compiler.py`
- Compatibility:
  - Runtime default is docker for consistent TeX environment across dev/prod/CI
- Rollback:
  - Set `LATEX_RUNTIME_MODE=host` or revert the `compiler.py` change

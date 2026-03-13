# Tasks: add-switchable-latex-runtime-executor

## 1. Implementation
- [x] 1.1 Define executor abstraction and concrete executors in `backend/app/services/latex/compiler.py`.
- [x] 1.2 Add executor factory reading `LATEX_RUNTIME_MODE` and `LATEX_DOCKER_IMAGE`.
- [x] 1.3 Integrate executor into `compile_latex` before subprocess invocation.
- [x] 1.4 Integrate executor into `_compile_latex_direct` before subprocess invocation.
- [x] 1.5 Preserve existing subprocess timeout, cwd, stdout/stderr capture, exception handling, fallback order, and `_kill_process_tree` behavior.
- [x] 1.6 Enforce runtime default as docker; host path is opt-in via explicit `LATEX_RUNTIME_MODE=host`.

## 2. Verification
- [x] 2.1 Validate default (unset mode) resolves to docker executor.
- [x] 2.2 Validate explicit `LATEX_RUNTIME_MODE=host` preserves host-path behavior.
- [x] 2.3 Validate invalid `LATEX_RUNTIME_MODE` falls back to docker with warning.
- [x] 2.4 Validate docker mode command wrapping includes `docker run --rm`, working directory mapping, and no `shell=True`.
- [x] 2.5 Validate output directory path mapping remains stable between host and docker execution modes.
- [x] 2.6 Validate fallback sequencing and error handling logic remain unchanged by integration point.
- [x] 2.7 Validate diagnostics channels remain intact (`stdout`/`stderr` capture unchanged).

## 3. OpenSpec Validation
- [x] 3.1 Run `openspec validate add-switchable-latex-runtime-executor --strict --no-interactive`.
- [x] 3.2 Resolve validation issues (if any) and rerun until clean.

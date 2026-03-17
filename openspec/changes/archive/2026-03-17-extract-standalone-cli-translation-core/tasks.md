# Implementation Tasks

- [x] Create OpenSpec proposal, design, task list, and spec deltas for standalone CLI extraction.
- [x] Copy the current backend translation kernel into `NiuTrans/LaTeXTrans/src`.
- [x] Add local runtime adapters for settings, clock, progress, concurrency, and async blocking.
- [x] Rewrite extracted imports to remove `backend.app.*` dependencies.
- [x] Replace legacy `main.py` with a standalone CLI entry that preserves old flag compatibility.
- [x] Replace legacy `compile.py` and `tool_agents/*` with compatibility wrappers around the extracted core.
- [x] Remove Streamlit from the open-source surface and trim the CLI dependency manifest.
- [x] Update README files to describe the standalone CLI artifact.
- [x] Add standalone CLI tests for argument parsing and no-web import expectations.
- [x] Run `openspec validate extract-standalone-cli-translation-core --strict --no-interactive`.
- [x] Run targeted Python validation for the extracted CLI package.

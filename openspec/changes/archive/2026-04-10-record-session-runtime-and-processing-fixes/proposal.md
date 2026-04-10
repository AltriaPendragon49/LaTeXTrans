# Why
- This session implemented several runtime, backend, and frontend fixes without a single OpenSpec change tying them together.
- The affected areas are easy to regress because they span deployment wiring, authentication, LaTeX parsing edge cases, community-agent persistence, and a dense processing workbench layout.
- Recording the current behavior in OpenSpec reduces future drift between shipped code and the repository's formal truth.

## What Changes
- Document the runtime requirement that local auth and community persistence boot with a configured business database URL.
- Document that the in-app login flow accepts an email address or phone number identifier.
- Document MySQL-compatible timestamp normalization for community-agent conversation, run, and event persistence.
- Document LaTeX include resolution behavior when `\input` or `\include` points at a directory-like path instead of a real file.
- Document the Processing page as a fixed-height, first-screen workbench whose live log scrolls only inside the dedicated log panel.

## Impact
- Affected specs: `deployment-infra`, `user-auth`, `community-agent-assistant`, `latex-translation-core`, `web-ui`
- Affected code: `backend/.env`, `backend/app/repositories/community_agent_repository.py`, `backend/app/services/latex/parser.py`, `backend/app/services/latex/utils.py`, `frontend/src/pages/Processing.tsx`, `frontend/src/components/log-viewer.tsx`, `frontend/src/pages/Login.tsx`

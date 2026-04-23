# Change: Restore admin-only Paper Copilot entry

## Why
The community agent runtime is currently retained in the codebase, but the product hides all direct UI access to it for every user. Product needs to restore the agent conversation workspace only for authenticated admin accounts while keeping it hidden and inaccessible for ordinary users.

## What Changes
- Restore a dedicated admin-only `Paper Copilot` sidebar entry under `Paper Tool`
- Enforce frontend route gating so unauthenticated users are redirected to login and authenticated non-admin users are redirected away from `/agent`
- Refresh the conversation workspace visuals with a moderate polish pass while preserving the current information architecture

## Impact
- Affected specs: `community-agent-assistant`, `web-ui`
- Affected code: `frontend/src/layout/AppSidebar.tsx`, `frontend/src/App.tsx`, `frontend/src/pages/community-conversation/index.tsx`, `frontend/src/features/community-conversation/components/*`, related frontend tests and locale resources

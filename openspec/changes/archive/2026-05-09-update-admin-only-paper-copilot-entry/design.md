## Context
The frontend already has an authenticated community conversation workspace and a reusable admin-role helper, but the shared shell currently hides all product entry points to the agent and the `/agent` route itself is not restricted to admins. Product wants to restore this capability only for admin accounts and improve the workspace presentation without changing the underlying runtime or conversation model.

## Goals
- Restore a discoverable admin-only entry to the retained conversation workspace
- Prevent guests and ordinary users from using `/agent` directly
- Improve visual hierarchy and polish for the existing conversation workspace

## Non-Goals
- Reintroduce public homepage or paper-detail agent entry points
- Change the backend community-agent runtime or conversation persistence model
- Redesign the conversation workspace information architecture from scratch

## Decisions
- Use existing `hasAdminRole(user?.roles)` as the single frontend authority for admin visibility and route access
- Add a new top-level sidebar item labeled `Paper Copilot` immediately after `Paper Tool`
- Enforce access at the route/page boundary so direct `/agent` navigation is blocked even when the sidebar link is hidden
- Keep the current workspace layout (`ConversationRail` + main panel + composer) and apply a moderate visual refresh through class and component styling updates

## Alternatives Considered
- Putting the entry inside the account menu: rejected because the request explicitly asks for placement under `Paper Tool`
- Allowing any authenticated user to access `/agent` while only hiding the sidebar item: rejected because direct route access would still expose the feature to ordinary users
- Performing a full layout redesign: rejected because the requested scope is a moderate polish pass, not a structural rewrite

## Risks / Trade-offs
- Redirecting non-admin users away from `/agent` changes an existing reachable route, so tests must explicitly cover both guest and non-admin cases
- Visual polish inside the current layout must preserve streaming, citations, actions, and existing controls; style-only changes should avoid behavioral regressions

## Migration Plan
1. Update specs to describe the new admin-only availability and UI expectations
2. Add the admin-only sidebar entry and route guard
3. Refresh workspace styling while keeping current behaviors intact
4. Verify through focused route and UI tests

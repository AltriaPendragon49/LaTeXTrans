# Change: Execute a community-first full frontend architecture rollout

## Why
The frontend no longer has a single mismatch to fix. It has three overlapping problems:

- the information architecture still mixes a community-reading product with a tools-first workspace mental model
- the UI language is inconsistent across navigation, cards, forms, and page shells
- the codebase structure still hides ownership behind technical folders, which makes large-scale changes brittle

The project now needs a full frontend rollout rather than another local page refactor. The rollout must keep feature coverage intact while reorganizing the product into a community-first application shell, a normalized `ui/` system, feature-based ownership, and cleaner state boundaries.

## What Changes
- Upgrade the current frontend-governance change from planning-only to implementation-driving rollout scope
- Rebuild the frontend as a community-first application with a magazine-like homepage and reading-first shell
- Replace the current hover-expand sidebar with a persistent primary navigation designed for content discovery
- Move the tools-hub panel model to real route pages for translate, workspace history, workspace settings, and glossary
- Keep route files as composition boundaries while moving reusable workspace and comparison surfaces into `features/translation-workflow` and `features/user-workspace`
- Restrict unauthenticated users to browse/read-only access while requiring login for translation, history, settings, glossary, and other workspace capabilities
- Keep admin functionality in the main navigation, but only render those entries for admins
- Establish a Uiverse-first component sourcing policy for reusable UI primitives, with all adopted patterns normalized inside `src/ui/`
- Expand the architecture migration from a single-page pilot to a whole-app rollout covering shell, routes, shared UI, state boundaries, and core feature pages
- Preserve functional coverage while allowing route organization, layout hierarchy, visual language, and internal state composition to change

## Impact
- Affected specs:
  - `frontend-architecture-governance`
  - `web-ui`
  - `community-paper-discovery-ui`
  - `community-public-read-experience`
  - `user-settings`
- Affected code:
  - `frontend/src/**/*`
- Runtime impact:
  - major frontend shell, route, UI-system, and state-boundary changes
- Delivery mode:
  - spec-first implementation in the existing isolated worktree and branch

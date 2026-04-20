## 1. OpenSpec And Rollout Foundation
- [x] 1.1 Expand this change from governance-only scope to full community-first frontend rollout scope
- [x] 1.2 Validate the updated change against all affected spec deltas
- [x] 1.3 Keep the existing isolated worktree and branch as the canonical rollout environment

## 2. UI System And Shell
- [x] 2.1 Create or normalize `frontend/src/ui/` as the only reusable primitive layer
- [x] 2.2 Audit high-priority primitives against Uiverse first and adapt selected patterns into the local UI system
- [x] 2.3 Add shared tokens for color, spacing, radius, shadow, typography, and motion under `frontend/src/styles/`
- [x] 2.4 Replace the current hover-expand sidebar with a persistent editorial main navigation
- [x] 2.5 Update the shared layout shell to support community-first navigation, admin entries, and account actions

## 3. Route And Information Architecture
- [x] 3.1 Introduce explicit route pages for `home`, `translate`, `workspace-history`, `workspace-settings`, and `workspace-glossary`
- [x] 3.2 Retire `ToolsHub` as an architectural center and replace it with redirects or compatibility routes only
- [x] 3.3 Ensure legacy utility routes redirect cleanly to their new canonical route destinations
- [x] 3.4 Enforce anonymous browse/read-only access and authenticated workspace access

## 4. Community Surfaces
- [x] 4.1 Rebuild the homepage as a magazine-like community-first discovery surface without reducing feed/search capability
- [x] 4.2 Preserve and integrate the PaperDetail pilot inside the new application shell
- [x] 4.3 Migrate community-paper reusable modules into `features/community-paper/`
- [x] 4.4 Keep reader-first behavior, translated mode controls, and paper-scoped support surfaces working after shell migration
- [x] 4.5 Add homepage paper-card action chips for source download, translated download, arXiv, and GitHub using the shared UI system

## 5. Translation And Workspace Surfaces
- [x] 5.1 Move dashboard translation workflow into a dedicated `/translate` page with clearer composition boundaries
- [x] 5.2 Split history, settings, and glossary into explicit workspace routes
- [x] 5.3 Preserve all current page capabilities while improving route clarity and UI consistency
- [x] 5.4 Ensure settings and history remain auth-gated and continue using existing backend contracts

## 6. Admin Surfaces
- [x] 6.1 Keep admin curation and admin task pages reachable through main navigation for admins only
- [x] 6.2 Preserve non-admin hiding behavior for all admin navigation and actions
- [x] 6.3 Normalize admin pages into the new shell and UI system

## 7. State And Compatibility Cleanup
- [x] 7.1 Move translation workflow ownership behind `features/translation-workflow/store/useTranslationStore.ts` and feature-facing hooks
- [x] 7.2 Preserve behavior with only the runtime redirects still needed during route migration
- [x] 7.3 Remove obsolete transitional structures only after the new routes and features are verified

## 8. Verification
- [x] 8.1 Add or update route, auth-boundary, navigation, and key feature tests for the new shell
- [x] 8.2 Run targeted frontend tests for community, translate, workspace, and admin flows
- [x] 8.3 Run a production frontend build and fix any path, type, or route regressions

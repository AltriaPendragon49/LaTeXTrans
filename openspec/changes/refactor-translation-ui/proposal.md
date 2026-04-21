# Refactor Translation UI

Remove the fragmented, "boxed" component aesthetic from the Translation Workspace and History Workspace. This change introduces a minimal, seamless layout that coordinates more naturally with the AppSidebar, creating a modern unified application feel rather than a dashboard of floating cards.

## Context
The current translation tool pages are structured tightly around nested `<Card>` primitives and `Shadow` utilities. This isolates the functional areas (like the ArXiv loader, configurations, and history tables) creating a visually disjointed layout with excessive borders and backgrounds. The UI must be refactored towards an edge-to-edge workspace that blends perfectly with the application shell.

## Scope
- Refactor `TranslationWorkspace.tsx` layout structure (tabs, configuration panels, bottom bar).
- Refactor `HistoryWorkspace.tsx` (remove DataTable borders/shadows, flatten expandable rows).
- Ensure smooth color and spatial transition between `AppSidebar` and the central workspaces.

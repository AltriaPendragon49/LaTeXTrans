# Why
- The current community shell and shared navigation are effectively hard-wired to a dark-only presentation, which blocks a readable daytime experience for users who browse in bright environments.
- The existing palette has already become part of the product identity, so it should be preserved as the canonical dark theme instead of being replaced.
- Theme choice should behave like other user-facing UI preferences: visible, intentional, and persistent across routes.

## What Changes
- Add a shared day/dark theme system for the frontend shell, with the current palette preserved as the dark mode baseline.
- Introduce a bright daytime palette centered on white and other high-luminance neutrals for the shared shell and community reading surfaces.
- Add a shared theme toggle button in the authenticated application shell so users can switch between day and dark modes without leaving the current page.
- Persist the selected theme mode across navigation and reloads.
- Refactor the community feed/detail reading surfaces and shared shell tokens so both themes remain legible and visually coherent.

## Impact
- Modifies capabilities `web-ui` and `community-paper-discovery-ui`.
- Touches frontend theme bootstrapping, shared layout/sidebar/header controls, community feed/detail surfaces, and locale files.
- Requires frontend unit tests and i18n validation as part of delivery.

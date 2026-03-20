# Overview
Implement a two-mode frontend theme system that keeps the current visual language as dark mode while adding a bright, paper-like daytime alternative. The change should be global at the shell level, but the first complete token migration target is the community browsing and reading flow because it currently contains the most hard-coded dark surfaces.

## Decisions

### Theme source of truth
- Use `next-themes` as the runtime theme controller because it already exists in the frontend dependency graph.
- Configure the provider for `light` and `dark` only, disable system auto-switching, and default to `dark` so current users retain the existing appearance until they opt into daytime mode.

### Token strategy
- Keep semantic Tailwind tokens for the base application.
- Add shell/community-specific CSS variables for high-contrast surfaces, borders, text hierarchy, pill backgrounds, and CTA accents.
- Replace hard-coded dark values in the shared shell and community pages with those variables so both modes stay readable without duplicating component trees.

### Control placement
- Place the toggle next to the existing language selector in the shared header because it is global, preference-like, and available on the routes where the user already navigates between community and translation work.
- Use an icon + localized label treatment with an accessible aria-label describing the next theme action.

### TDD scope
- Add unit tests for the toggle behavior itself and the shared layout integration.
- Reuse a configurable `next-themes` mock so tests can assert the correct `setTheme(...)` calls without depending on browser theme APIs.

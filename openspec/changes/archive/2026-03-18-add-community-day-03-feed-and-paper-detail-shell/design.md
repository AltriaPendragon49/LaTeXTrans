# Day 3 Design: Community Feed / Paper Detail Shell

## Context
Day 2 established the community `papers` API and official-first admission rules, but the frontend still opens on the translation Dashboard. Day 3 turns the product into a visible community experience by making the homepage a paper-discovery surface while preserving the old translation workflow at a secondary route.

## Route Decisions
- `/` becomes the community Feed homepage
- `/paper/:paperId` becomes the community paper detail shell
- `/translate` preserves the existing translation Dashboard
- Existing routes such as `/processing`, `/preview`, `/history`, `/settings`, `/profile`, and `/login` remain intact

This route migration is required because the community is now a first-class product surface instead of a hidden API contract.

## alphaXiv Reference Boundaries
Day 3 references `https://www.alphaxiv.org/` for:
- research-exploration pacing
- dense information cards
- dark reading environment
- tool-belt detail page rhythm

Day 3 must not copy:
- alphaXiv brand, naming, or navigation taxonomy
- assistant, notes, blog, labs, or comments product surfaces
- alphaXiv interaction patterns for likes/bookmarks/comments
- alphaXiv colors, iconography, or exact composition

The intended result is “a restrained research-reading interface inspired by alphaXiv” rather than “an alphaXiv skin.”

## Visual System
### Direction
- dark editorial research surface
- editorial order over social noise
- official-first signals visible but restrained

### Color
- background: neutral charcoal / graphite
- panel: lifted dark gray with brightness separation rather than color tint
- primary accent: muted cool gray-blue reserved for the official state, active tabs, and the single primary CTA
- supporting accents are removed from normal body copy and descriptive surfaces
- official: low-saturation cool highlight
- fallback: neutral slate

### Emphasis Rules
- color acts as air and marking, not emotional tone
- gray-scale readability must hold without relying on hue
- titles, spacing, and grouping carry hierarchy before color does
- shared shell must not repeat a `Research Console` kicker label if it adds width or clutter

### Motion
- 150–250ms micro-interactions
- transform/opacity only
- respect `prefers-reduced-motion`
- no large ambient animation fields

### Density
- cards carry status + metadata + counters + asset summary
- detail page separates reading zone from future-action zone
- titles remain visually dominant while secondary metadata stays scannable
- sidebar stays compact and avoids large decorative copy blocks in expanded mode

## Component Constraints
### Feed
- Hero block introduces the community surface
- segmented control switches `latest` / `translated` / `hot`
- search field is a Day 3 placeholder that still binds to the Day 2 `q` parameter
- list items must render loading, empty, and error states without mock fallback

### Paper Card
- show community status and translation status as separate badges
- show author summary, category summary, timing, counters, and latest asset summary
- official papers must be visually distinguishable from fallback papers

### Detail
- render title, authors, categories, abstract, counters, selected task, and selected asset
- fire the view-count request after successful detail load
- if view tracking fails, do not block content rendering

### Action Shell
- action slots remain visible but disabled
- each slot explains that the capability lands in later changes
- no fake navigation and no hidden active handlers

## Accessibility Rules
- touch targets at least 44x44
- icon-only affordances require `aria-label`
- focus rings must remain visible on the dark surface
- color is never the only state indicator
- skeletons reserve layout height to avoid jumping

## Data Flow
### Feed
- consume `GET /api/papers?sort=...&q=...`
- render loading → success/empty/error states
- no local mock source

### Detail
- consume `GET /api/papers/{paperId}`
- then call `POST /api/papers/{paperId}/view`
- treat view tracking as fire-and-forget

## Compatibility
The legacy `web-ui` assumption that “homepage = Dashboard” becomes invalid once the community Feed takes over `/`. Day 3 therefore includes a `web-ui` delta so the translation workspace is formally relocated to `/translate`.

## Forward Compatibility
Day 4 and later changes will wire the disabled action shell to:
- translation trigger
- preview
- download
- likes/favorites/comments
- report entry

Day 3 must therefore preserve stable action positions rather than hiding those controls entirely.

# Why
- Day 2 already established the community paper API, but the product still opens on the old translation workspace instead of a community browse surface.
- The community MVP now needs a visible homepage and paper detail shell that present official-first community content as a credible research discovery experience.
- The UI must reference alphaXiv's research-exploration cadence without copying its brand, navigation model, or interaction system.

## What Changes
- Move the frontend homepage route `/` to a community Feed shell and relocate the existing translation Dashboard to `/translate`.
- Add a graphite-dark community Feed and paper detail shell that directly consume Day 2 paper APIs.
- Define paper card, detail metadata, and disabled action slots for future translation, preview, download, and interaction changes.
- Update the UI contract so the homepage is community-first while preserving the old translation workspace as a stable secondary route.
- Keep the shared shell visually restrained: neutral dark surfaces, low-saturation official emphasis, and no redundant `Research Console` kicker label.

## Impact
- Adds capability `community-paper-discovery-ui`.
- Modifies the existing `web-ui` capability so the product homepage becomes the community Feed and the translation workspace lives at `/translate`.
- Depends on `add-community-day-02-paper-intake-and-feed-api`.
- Provides the visual target for Day 4 paper translation actions and later interaction/moderation changes.

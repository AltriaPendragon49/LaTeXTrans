# Why
- Day 3 needs visible community surfaces so the MVP stops looking like a hidden backend contract.
- The source plan explicitly calls for a Feed homepage, three list views, and a paper detail shell with status and action slots.
- A focused UI shell change keeps scope narrow while giving later changes stable targets for translation and interactions.

## What Changes
- Define the Feed homepage shell, including latest, translated, and hot placeholder views.
- Define the paper card and paper detail shell content contract.
- Limit the day to browse and view surfaces; action wiring remains for later changes.

## Impact
- Adds capability `community-paper-discovery-ui`.
- Depends on `add-community-day-02-paper-intake-and-feed-api`.
- Provides the UI target for Day 4 translation actions and Day 6 interactions.

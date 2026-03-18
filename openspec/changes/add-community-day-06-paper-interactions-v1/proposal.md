# Why
- Day 6 adds the minimum community loop that makes papers feel social rather than purely operational.
- The source plan narrows the interaction scope to likes, favorites, and single-level comments to stay inside MVP limits.
- This change isolates interaction behavior from moderation and notification follow-up so each day remains executable.

## What Changes
- Define the like, favorite, and comment v1 behavior for paper detail and Feed counters.
- Define counter consistency between interaction writes and read models.
- Keep replies and advanced comment trees out of scope for this change.

## Impact
- Adds capability `community-interactions-v1`.
- Depends on `add-community-day-05-week1-e2e-stabilization`.
- Enables Day 7 notifications and Day 8 moderation follow-up flows.

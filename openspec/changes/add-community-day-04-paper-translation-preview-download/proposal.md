# Why
- Day 4 is where the community paper object must actually connect to the existing translation engine.
- The current product already has processing and preview surfaces, but the new community detail page needs a paper-driven entry to those flows.
- Download control also needs a clear contract so community access does not bypass permission checks.

## What Changes
- Define the paper-based translation trigger, preview read path, and controlled download path.
- Define how the latest successful translation asset is attached back to a paper record.
- Keep scope focused on bridge behavior and permission checks, not on new translation engine internals.

## Impact
- Adds capability `community-paper-translation-bridge`.
- Depends on `add-community-day-03-feed-and-paper-detail-shell`.
- Bridges the community MVP to existing processing and preview flows.

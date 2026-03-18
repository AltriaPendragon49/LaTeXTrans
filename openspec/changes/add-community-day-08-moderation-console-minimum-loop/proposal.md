# Why
- Day 8 turns user reports into an actual governance loop.
- The source plan keeps moderation deliberately small: report queue, basic resolution actions, and hidden-content behavior.
- A dedicated moderation change prevents governance scope from leaking into broader admin platform work.

## What Changes
- Define the admin report queue and report resolution contract.
- Define the minimum moderation actions for ignoring or hiding content, with user-ban kept as a placeholder.
- Define the frontstage visibility rule after content is hidden.

## Impact
- Adds capability `community-moderation-loop`.
- Depends on `add-community-day-07-notifications-and-report-entry`.
- Completes the minimum governance loop required by the 10-day MVP.

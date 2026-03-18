# Why
- Day 7 adds the minimum system feedback and safety entry points required after interactions go live.
- The source plan explicitly limits notifications to a simple in-site list and limits reports to an entry flow rather than a full admin console.
- Separating the report entry step from the moderation console keeps daily scope realistic.

## What Changes
- Define a minimal notifications list for user-visible system messages.
- Define the user-facing report submission flow from paper detail and comment surfaces.
- Keep real-time delivery and admin resolution out of scope for this day.

## Impact
- Adds capability `community-notifications-reporting`.
- Depends on `add-community-day-06-paper-interactions-v1`.
- Provides the input stream consumed by Day 8 moderation handling.

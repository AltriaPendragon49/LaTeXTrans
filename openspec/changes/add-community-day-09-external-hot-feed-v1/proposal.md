# Why
- Day 9 adds an operations entry point without turning the MVP into a ranking-engine project.
- The source plan explicitly recommends an external hot list mirror instead of an internal hot-score system.
- This change gives the Feed a growth surface while preserving the stability of the main paper workflow.

## What Changes
- Define an external hot paper import flow for AlphaXiv or an equivalent source.
- Define the Feed presentation and source labeling for the imported hot list.
- Define minimum stability work such as logging, rate control, and failure containment for the import path.

## Impact
- Adds capability `community-external-hot-feed`.
- Depends on `add-community-day-08-moderation-console-minimum-loop`.
- Keeps internal ranking, recommendation, and real-time scoring out of scope.

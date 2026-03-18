## ADDED Requirements
### Requirement: Community MVP demo and handoff package
The system SHALL finish the 10-day rollout with a repeatable demo package, a known-issues record, and a synchronized execution ledger for follow-up work.

#### Scenario: Run the MVP demo path
- **WHEN** the final demo is prepared
- **THEN** the system SHALL define a repeatable route covering homepage browse, paper detail, translation, preview or download, interaction, report entry, and moderation handling
- **AND** the route SHALL reference the demo data needed to keep the presentation stable.

#### Scenario: Capture known issues and next-step decisions
- **WHEN** the 10-day rollout closes
- **THEN** the system SHALL record the unresolved issues, operational caveats, and Week 3 backlog items
- **AND** the backlog SHALL explicitly cover Redis or Celery adoption, hot-feed evolution, and notification delivery upgrades.

#### Scenario: Keep status synchronized at handoff
- **WHEN** a daily change is marked complete in the final handoff package
- **THEN** the corresponding `tasks.md` checklist SHALL remain the task-level source of truth
- **AND** the 10-day index SHALL only be updated after the checklist and validation state are already current.

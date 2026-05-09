## MODIFIED Requirements
### Requirement: Feed sort and browse shell
The community homepage SHALL provide the browse controls needed to inspect published community papers using the production sort semantics, without communicating an official-vs-fallback hierarchy.

#### Scenario: Switch feed views
- **WHEN** a user changes between `latest`, `views`, and `likes`
- **THEN** the system SHALL request the matching community paper list from the backend API
- **AND** the feed SHALL render loading, empty, and error states without falling back to local mock data.

#### Scenario: Sort values fall back to the latest rule
- **WHEN** multiple community papers share the same `view_count` or `like_count`
- **THEN** the UI SHALL treat the backend order as canonical
- **AND** that canonical order SHALL break ties using original arXiv publication time descending
- **AND** it SHALL continue falling back to `official_published_at` and then `created_at` when original publication time is unavailable.

#### Scenario: Public feed copy treats published papers as peer entries
- **WHEN** the feed homepage renders
- **THEN** the page SHALL present the community library as one published-paper surface
- **AND** it SHALL NOT communicate that official papers are prioritized over fallback papers
- **AND** it SHALL NOT explain feed ranking through `community_status` tiers.

### Requirement: Paper card content contract
Each feed result SHALL render as a dense paper discovery card that helps the viewer decide whether to inspect the paper in detail without relying on public status-tier badges.

#### Scenario: Render a paper card
- **WHEN** the feed receives a community paper item
- **THEN** the card SHALL show translation status, title, author summary, category summary, publication timing, counters, engagement affordances, and selected asset summary
- **AND** it SHALL NOT require an official-vs-fallback badge or priority styling to explain why the paper appears where it does.

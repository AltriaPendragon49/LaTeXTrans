## ADDED Requirements
### Requirement: alphaXiv sitemap-driven paper catalog export
The repository SHALL provide a script that enumerates alphaXiv paper pages from the public sitemap index and exports de-duplicated arXiv IDs to a Markdown document.

#### Scenario: Export all discoverable papers
- **WHEN** an operator runs the alphaXiv export script from the repository
- **THEN** the script SHALL read the public alphaXiv sitemap index
- **AND** it SHALL expand all paper sitemap shards referenced by that index
- **AND** it SHALL filter sitemap entries down to primary `/abs/<id>` paper URLs
- **AND** it SHALL collect each discoverable arXiv ID exactly once
- **AND** it SHALL write a Markdown file under `alphaxiv/` containing the resulting ID set.

#### Scenario: Malformed sitemap entries do not break export
- **WHEN** a paper sitemap contains malformed XML or non-primary `/abs/<id>/...` routes
- **THEN** the script SHALL still extract valid primary paper URLs from that shard
- **AND** it SHALL ignore non-primary paper routes
- **AND** it SHALL continue processing the remaining sitemap shards.

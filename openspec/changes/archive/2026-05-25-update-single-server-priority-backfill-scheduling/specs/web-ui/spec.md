## ADDED Requirements
### Requirement: Community feed loads incrementally
The community homepage UI MUST load public papers incrementally instead of fetching the entire feed on first render.

#### Scenario: User opens the homepage feed
- **WHEN** the user opens the community feed
- **THEN** the UI MUST request only the first page from the papers API
- **AND** it MUST render the current total count without requiring the full item list in memory.

#### Scenario: User asks for more feed items
- **WHEN** the current feed response reports `has_more=true`
- **THEN** the UI MUST offer a load-more action
- **AND** clicking it MUST request the next page using `next_offset`
- **AND** append those items to the existing feed instead of replacing the whole list.

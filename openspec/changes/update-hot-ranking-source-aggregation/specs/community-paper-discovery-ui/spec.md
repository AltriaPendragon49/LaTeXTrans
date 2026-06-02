## ADDED Requirements
### Requirement: Hot feed exposes publication-date window filtering
The community homepage SHALL let users filter the `Hot` feed by arXiv publication-date windows.

#### Scenario: User changes the hot publication-date window
- **WHEN** a user selects `3 Days`, `7 Days`, `30 Days`, `90 Days`, or `All time` while viewing the `Hot` feed
- **THEN** the UI SHALL request and render hot results for the selected window
- **AND** the window SHALL be interpreted by canonical arXiv publication date rather than local community publication time.

#### Scenario: Active window is visible and resettable
- **WHEN** a finite or non-default hot window is active
- **THEN** the browse controls SHALL show a compact active window pill
- **AND** activating the pill reset affordance SHALL return the feed to the default hot window.

### Requirement: Feed filter control uses anchored popover on desktop
The community homepage SHALL add a filter icon beside the sort tabs and use it to open publication-date filters.

#### Scenario: Desktop user opens the feed filter
- **WHEN** a desktop-width user activates the filter icon placed immediately to the left of the feed sort control
- **THEN** an anchored popover SHALL open below the filter icon
- **AND** it SHALL expose publication-date choices for `3 Days`, `7 Days`, `30 Days`, `90 Days`, and `All time`
- **AND** selecting a choice SHALL update the active hot window and refresh the feed.

#### Scenario: Filter popover remains scoped
- **WHEN** the filter popover opens in this version
- **THEN** it SHALL focus on publication-date filtering
- **AND** it SHALL NOT show nonfunctional topic search controls unless topic filtering is implemented by the backend.

### Requirement: Feed filter control remains usable on narrow screens
The community homepage SHALL provide a mobile-safe equivalent of the feed filter popover.

#### Scenario: Mobile user opens the feed filter
- **WHEN** a narrow-screen user activates the filter icon
- **THEN** the UI SHALL open a bottom sheet or similarly explicit secondary surface
- **AND** the publication-date choices SHALL remain reachable without overlapping the sort tabs, search box, or feed cards.

#### Scenario: Mobile controls avoid cramped wrapping
- **WHEN** the active hot window pill and sort controls render on a narrow screen
- **THEN** the controls SHALL wrap or stack predictably
- **AND** labels, icons, and active states SHALL not overlap or clip.

### Requirement: Hot feed explains ranking freshness
The community homepage SHALL show a compact explanation of the `Hot` ranking algorithm and refresh cadence only while the `Hot` feed is active.

#### Scenario: User views the hot feed explanation
- **WHEN** a user views the `Hot` feed
- **THEN** the UI SHALL show a compact pill-like explanation row below the feed sort controls and above the paper list
- **AND** the explanation SHALL state that the ranking combines public attention, scholarly impact, implementation signals, and local engagement
- **AND** the explanation SHALL state that the hot list refreshes daily.

#### Scenario: User switches away from the hot feed
- **WHEN** a user changes from `Hot` to `Latest`, `Views`, or `Likes`
- **THEN** the hot-ranking explanation SHALL no longer be visible.

#### Scenario: Hot explanation keeps tight spacing
- **WHEN** the hot-ranking explanation renders on desktop or narrow screens
- **THEN** it SHALL preserve compact vertical spacing between the sort row and the first paper card
- **AND** its text SHALL wrap without overlapping the filter controls, active window pill, or paper content.

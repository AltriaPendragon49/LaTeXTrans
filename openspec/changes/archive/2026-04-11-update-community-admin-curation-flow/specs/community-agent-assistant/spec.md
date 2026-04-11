## ADDED Requirements
### Requirement: Community agent runtime can stay retained while product UI entry points are hidden
The community agent runtime SHALL remain restorable from retained code assets even when the product hides its public homepage, sidebar, and paper-detail entry points and disables direct product access to those agent flows.

#### Scenario: Product hides public agent UI entry points
- **WHEN** the current product configuration hides the homepage agent composer, sidebar agent affordances, and paper-detail public copilot pane
- **THEN** the retained backend runtime code and underlying tool-calling services SHALL remain present in the codebase
- **AND** ordinary users and admins SHALL NOT be able to use those product agent flows directly in the current hidden mode
- **AND** later recovery of those UI entry points SHALL not require reintroducing deleted runtime code.

## REMOVED Requirements
### Requirement: Community homepage uses an agent-first research entry
**Reason**: The homepage is being changed to internal community-paper search to reduce exposed public agent cost and keep the community surface curated.
**Migration**: The community-agent runtime and dedicated conversation route remain retained for future recovery, but the homepage no longer uses a public agent-first entry as its primary contract.

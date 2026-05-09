## ADDED Requirements
### Requirement: Account Block Shows Translation Quotas
The lower-left account/settings/logo block SHALL display both the local LaTeX translation quota and NiuTrans PDF direct-translation credits without confusing the two quota sources.

#### Scenario: Expanded account block displays both quotas
- **WHEN** an authenticated user views the expanded desktop account/settings/logo area
- **THEN** the block SHALL be tall enough to display two quota cells without overlap
- **AND** the left cell SHALL show `LaTeX 翻译：remaining/limit`, such as `LaTeX 翻译：3/3`
- **AND** the right cell SHALL show `PDF 直译：unusedNumIntegral积分`, such as `PDF 直译：60积分`
- **AND** the PDF direct-translation value SHALL come from the backend's NiuTrans `unusedNumIntegral` snapshot.

#### Scenario: Quotas are independent in UI copy
- **WHEN** the quota block renders
- **THEN** the UI SHALL present LaTeX translation as a daily `remaining/limit` allowance
- **AND** it SHALL present PDF direct translation as a积分 balance
- **AND** it SHALL NOT display PDF direct translation as `3/3` or imply that the two quota sources offset each other.

#### Scenario: Quota snapshot is loading or unavailable
- **WHEN** local quota or NiuTrans credit data is still loading, unavailable, or stale
- **THEN** the account block SHALL keep a stable layout
- **AND** it SHALL show an i18n-managed loading, unavailable, or stale state for the affected cell
- **AND** it SHALL avoid blocking unrelated account/settings actions.

#### Scenario: Collapsed or mobile shell remains usable
- **WHEN** the sidebar is collapsed or the app uses a narrow/mobile shell
- **THEN** the quota display SHALL degrade into a compact, tooltip, or sheet presentation
- **AND** account actions, settings access, and navigation SHALL remain discoverable and non-overlapping.

#### Scenario: New quota copy uses i18n resources
- **WHEN** quota labels, fallback states, tooltips, or quota-exceeded messages are rendered in the frontend
- **THEN** all user-visible copy SHALL resolve through centralized i18n resources
- **AND** no new hardcoded user-visible quota strings SHALL be introduced in frontend source files.

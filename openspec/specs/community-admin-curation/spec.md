# community-admin-curation Specification

## Purpose
TBD - created by archiving change update-community-admin-curation-flow. Update Purpose after archive.
## Requirements
### Requirement: Admin curation page is visible only to local admins
The product SHALL expose the community curation page only to authenticated users with the local `admin` role.

#### Scenario: Admin user opens the shared shell
- **WHEN** an authenticated user with the local `admin` role renders the shared shell
- **THEN** the shell SHALL show the `社区论文新增入库` navigation entry
- **AND** visiting that page SHALL be allowed for that user.

#### Scenario: Non-admin user opens the shared shell
- **WHEN** an authenticated user without the local `admin` role renders the shared shell
- **THEN** the `社区论文新增入库` navigation entry SHALL be hidden
- **AND** the corresponding page route SHALL not be available as a normal product action.

### Requirement: Admin curation page supports both arXiv and archive intake
The admin curation page SHALL support official community-paper intake through `arXiv ID` entry and TeX-containing archive upload.

#### Scenario: Admin curates by arXiv id
- **WHEN** an admin enters an `arXiv ID` on the curation page
- **THEN** the page SHALL submit that item into the community curation pipeline
- **AND** the UI SHALL show tracked progress for that item.

#### Scenario: Admin curates by archive upload
- **WHEN** an admin uploads a TeX-containing archive on the curation page
- **THEN** the page SHALL submit that archive into the same community curation pipeline
- **AND** the UI SHALL show tracked progress for that item.

### Requirement: Admin curation page supports bounded-concurrency batch handling
The admin curation page SHALL support multi-item submission while using bounded parallelism behind the scenes.

#### Scenario: Admin submits a mixed or multi-item batch
- **WHEN** an admin submits multiple items in one curation batch
- **THEN** the system SHALL track each paper separately inside the batch
- **AND** the backend SHALL schedule execution with bounded concurrency to improve throughput without dropping the final publication quality bar.

### Requirement: Admin curation publishes only complete papers
The admin curation workflow SHALL only publish a paper into the community feed after all required curation stages have succeeded.

#### Scenario: Paper reaches complete curated state
- **WHEN** curation finishes metadata preparation, translation, structured insight generation, and persisted similar-recommendation generation successfully
- **THEN** the paper SHALL become visible in the community feed
- **AND** it SHALL appear as a complete curated paper rather than a processing placeholder.

#### Scenario: Paper has not completed required curation stages
- **WHEN** any required curation stage is still running or has failed
- **THEN** the paper SHALL remain outside the public community feed
- **AND** the UI SHALL not expose it as an incomplete community result.

### Requirement: Admin role assignment uses local role state after normal account creation
The product SHALL treat admin access as a local-role assignment layered on top of a normally created user account.

#### Scenario: Existing local user is granted admin
- **WHEN** an operator marks an existing local user record as `admin` through the supported local role mechanism
- **THEN** the next resolved session for that user SHALL include the `admin` role
- **AND** the community curation page and admin-only controls SHALL become available to that user.


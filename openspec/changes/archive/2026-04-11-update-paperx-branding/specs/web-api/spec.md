## MODIFIED Requirements
### Requirement: Email Notification Service
The system SHALL provide a background email service to notify users of task completion.

#### Scenario: Enabling completion emails
- **WHEN** a user enables task email notifications and a task later reaches a terminal state
- **THEN** the product SHALL use PaperX-branded completion or failure wording in its outward-facing notification surfaces
- **AND** the user-facing status email content SHALL keep the task identifier and terminal status details.

## ADDED Requirements
### Requirement: Public API metadata uses the current product brand
The API SHALL expose outward-facing service metadata using the current PaperX product brand.

#### Scenario: Root metadata reflects the current brand
- **WHEN** a client requests the API root endpoint
- **THEN** the response message and descriptive service metadata SHALL identify the backend as PaperX rather than legacy LaTeXTrans branding.

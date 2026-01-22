## ADDED Requirements

### Requirement: Web-Based User Interface
The system SHALL provide a modern, browser-based interface for LaTeX paper translation that allows non-technical users to interact with the translation service without CLI knowledge.

#### Scenario: User accesses the web application
- **GIVEN** the frontend server is running at http://localhost:5173
- **WHEN** user navigates to the URL in a modern browser
- **THEN** the main application interface loads successfully
- **AND** the interface displays tab options for "Upload File" and "arXiv ID"
- **AND** the interface is responsive across desktop, tablet, and mobile screen sizes

### Requirement: File Upload Interface
The system SHALL provide a drag-and-drop file upload mechanism for `.tex` and `.zip` files.

#### Scenario: User uploads a valid LaTeX file
- **GIVEN** user is on the "Upload File" tab
- **WHEN** user drags a `.tex` file into the upload zone
- **THEN** the file name and size are displayed
- **AND** an upload button becomes active
- **AND** clicking upload triggers the backend `/upload` API
- **AND** a task ID is received and stored

#### Scenario: User uploads an invalid file format
- **GIVEN** user is on the "Upload File" tab
- **WHEN** user attempts to upload a `.pdf` file
- **THEN** a validation error message is displayed
- **AND** the upload is prevented
- **AND** the error suggests accepted formats (`.tex`, `.zip`)

#### Scenario: User uploads a file exceeding size limit
- **GIVEN** user selects a file larger than 50MB
- **WHEN** the file is added to the upload zone
- **THEN** a size limit error is displayed
- **AND** the upload button remains disabled

### Requirement: arXiv Integration Interface
The system SHALL provide a text input for arXiv paper IDs that validates format and triggers automatic download.

#### Scenario: User submits a valid arXiv ID
- **GIVEN** user is on the "arXiv ID" tab
- **WHEN** user enters a valid ID (e.g., `2508.18791`)
- **AND** clicks the submit button
- **THEN** the input is validated against arXiv ID format
- **AND** the backend `/arxiv` API is called
- **AND** a task ID is received and stored
- **AND** a loading indicator appears during download

#### Scenario: User submits an invalid arXiv ID format
- **GIVEN** user enters an invalid format (e.g., `abc123`)
- **WHEN** user attempts to submit
- **THEN** a format validation error is displayed
- **AND** the submit button is disabled
- **AND** the error message shows the expected format

### Requirement: Real-Time Progress Tracking
The system SHALL display real-time translation progress through polling-based status updates.

#### Scenario: Progress updates during translation
- **GIVEN** a translation task has been started
- **WHEN** the frontend polls `/task/{taskId}` every 2 seconds
- **THEN** the progress bar updates to reflect current percentage (0-100%)
- **AND** the current stage is displayed ("Parsing", "Translating", "Compiling")
- **AND** relevant messages are shown (e.g., "Processing section 3/10")

#### Scenario: Translation completes successfully
- **GIVEN** a translation is in progress
- **WHEN** the backend returns status "completed"
- **THEN** the progress bar shows 100%
- **AND** polling stops automatically
- **AND** download buttons become visible
- **AND** a success message is displayed

#### Scenario: Translation fails with error
- **GIVEN** a translation is in progress
- **WHEN** the backend returns status "failed" with an error message
- **THEN** polling stops
- **AND** an error alert is displayed with the error message
- **AND** the interface allows the user to start a new translation

### Requirement: File Download Interface
The system SHALL provide download buttons for translated PDF and source files after successful translation.

#### Scenario: User downloads translated PDF
- **GIVEN** translation status is "completed"
- **WHEN** user clicks "Download PDF" button
- **THEN** the frontend calls `/download/{taskId}/pdf`
- **AND** the browser initiates file download
- **AND** the PDF file is saved with a descriptive filename

#### Scenario: User downloads translated source code
- **GIVEN** translation status is "completed"
- **WHEN** user clicks "Download Source" button
- **THEN** the frontend calls `/download/{taskId}/source`
- **AND** a `.zip` archive is downloaded
- **AND** the archive contains the translated `.tex` files

### Requirement: Cross-Browser Compatibility
The system SHALL function correctly across modern web browsers.

#### Scenario: Application works in Chrome
- **GIVEN** user accesses the application in Chrome (latest version)
- **WHEN** user performs any operation (upload, translate, download)
- **THEN** all features work correctly without errors

#### Scenario: Application works in Firefox
- **GIVEN** user accesses the application in Firefox (latest version)
- **WHEN** user performs any operation
- **THEN** all features work correctly without errors

#### Scenario: Application works in Edge
- **GIVEN** user accesses the application in Edge (latest version)
- **WHEN** user performs any operation
- **THEN** all features work correctly without errors

### Requirement: Error Handling and User Feedback
The system SHALL provide clear, user-friendly error messages for all failure scenarios.

#### Scenario: Backend API is unreachable
- **GIVEN** the backend server is not running
- **WHEN** user attempts any operation requiring API communication
- **THEN** a connection error message is displayed
- **AND** the message suggests checking if the backend is running
- **AND** the interface remains usable for retry

#### Scenario: Network timeout during file upload
- **GIVEN** user initiates a file upload
- **WHEN** the network connection is interrupted
- **THEN** an upload failure message is displayed
- **AND** the user can retry the upload
- **AND** the interface returns to ready state

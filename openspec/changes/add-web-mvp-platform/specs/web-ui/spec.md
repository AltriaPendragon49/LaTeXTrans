## ADDED Requirements

### Requirement: File Upload Interface
The system SHALL provide a browser-based interface for uploading LaTeX source files.

#### Scenario: Drag and drop file upload
- **WHEN** user drags a `.tex` or `.zip` file over the upload zone
- **THEN** the zone highlights with visual feedback, accepts the drop, uploads the file via `POST /upload`, and displays the returned task ID

#### Scenario: Click to browse file upload
- **WHEN** user clicks the upload zone
- **THEN** a file picker dialog opens, accepts `.tex` and `.zip` files, uploads selected file, and transitions to progress tracking view

#### Scenario: Invalid file type rejected by UI
- **WHEN** user attempts to upload a `.pdf` or unsupported file type
- **THEN** the UI shows an error message "Only .tex and .zip files are supported" without making an API call

#### Scenario: Upload progress indication
- **WHEN** file upload is in progress (POST /upload)
- **THEN** the UI displays upload percentage or spinner until task ID is received

### Requirement: arXiv ID Input Interface
The system SHALL provide a form for entering arXiv paper IDs to initiate translation.

#### Scenario: Valid arXiv ID submission
- **WHEN** user enters a valid arXiv ID (e.g., "2508.18791") and clicks "Translate"
- **THEN** the UI sends `POST /arxiv`, receives task ID, and transitions to progress tracking view

#### Scenario: arXiv ID format validation
- **WHEN** user enters text not matching arXiv ID pattern (XXXX.XXXXX)
- **THEN** the UI shows inline validation error "Invalid arXiv ID format (expected: XXXX.XXXXX)" before submission

#### Scenario: arXiv download failure handling
- **WHEN** backend returns error "Failed to download from arXiv"
- **THEN** the UI displays a user-friendly error with retry button

### Requirement: Translation Progress Display
The system SHALL show real-time translation progress with visual indicators and status messages.

#### Scenario: Progress bar updates
- **WHEN** task status is polled every 2 seconds via `GET /task/{task_id}`
- **THEN** the progress bar animates to reflect the current percentage (0-100%) and stage label updates

#### Scenario: Stage transitions
- **WHEN** task transitions from "parsing" → "translating" → "compiling"
- **THEN** the UI displays stage-specific icons and messages (e.g., "🔍 Parsing LaTeX structure...", "🌐 Translating text...", "📄 Compiling PDF...")

#### Scenario: Completion notification
- **WHEN** task status changes to "completed"
- **THEN** the UI stops polling, shows success message "✅ Translation complete!", and reveals PDF download button

#### Scenario: Completion with warnings notification
- **WHEN** task status changes to "completed_with_warnings"
- **THEN** the UI stops polling, displays warning message "⚠️ Translation completed with compilation warnings", shows both "Download PDF" and "Download Source" buttons, and displays a warning icon indicating imperfect compilation

#### Scenario: Compilation failure notification
- **WHEN** task status changes to "failed_compilation"
- **THEN** the UI stops polling, displays error message "❌ PDF compilation failed", shows "Download Source" button prominently with message "Download translated LaTeX source for manual compilation", and optionally shows "Retry" button

#### Scenario: General error notification
- **WHEN** task status changes to "failed" (non-compilation error)
- **THEN** the UI stops polling, displays error message from backend, and shows "Retry" button

### Requirement: Download Action Interface
The system SHALL provide buttons to download translated output files from completed tasks.

#### Scenario: Download PDF (successful compilation)
- **WHEN** user clicks "Download PDF" button for a task with status "completed" or "completed_with_warnings"
- **THEN** the browser initiates download of `GET /download/{task_id}/pdf` with filename `{project_name}.pdf`

#### Scenario: Download source code (successful translation)
- **WHEN** user clicks "Download Source" button for a task with status "completed", "completed_with_warnings", or "failed_compilation"
- **THEN** the browser initiates download of `GET /download/{task_id}/source` with filename `{project_name}_translated.zip`

#### Scenario: Download source only (compilation failed)
- **WHEN** task status is "failed_compilation" (no PDF available)
- **THEN** only "Download Source" button is visible with prominent styling and tooltip "PDF compilation failed. Download LaTeX source for manual compilation."

#### Scenario: Download buttons hidden before completion
- **WHEN** task status is "pending" or "processing"
- **THEN** download buttons are not visible (replaced by progress tracker)

### Requirement: UI Layout and Navigation
The system SHALL organize upload/input methods and progress tracking in an intuitive layout.

#### Scenario: Tab switching between upload methods
- **WHEN** user is on "Upload File" tab and clicks "arXiv ID" tab
- **THEN** the file upload form hides and arXiv input form appears without page reload

#### Scenario: Responsive design
- **WHEN** user accesses the UI on a mobile device or resizes browser window
- **THEN** layout adapts to screen size (stacks panels vertically on narrow screens)

#### Scenario: Accessibility compliance
- **WHEN** user navigates via keyboard (Tab, Enter)
- **THEN** all interactive elements (upload zone, input fields, buttons) are reachable and operable

### Requirement: Visual Design Standards
The system SHALL present a modern, professional interface using TailwindCSS styling.

#### Scenario: Premium aesthetic
- **WHEN** user first loads the application
- **THEN** the UI displays a clean, modern design with harmonious colors (not plain RGB colors), smooth gradients, and subtle shadows

#### Scenario: Interactive feedback
- **WHEN** user hovers over buttons or clickable elements
- **THEN** visual feedback is provided via color changes, scaling, or shadow effects

#### Scenario: Loading states
- **WHEN** any async operation is in progress (upload, API calls)
- **THEN** appropriate loading indicators (spinners, skeleton screens, or progress bars) are shown

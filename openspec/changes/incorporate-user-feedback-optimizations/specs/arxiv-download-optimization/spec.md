# ArXiv Download Optimization

## MODIFIED Requirements

### Requirement: Arxiv Download Progress Backend Throttling
The backend MUST throttle downloading progress to reduce DB IO.

#### Scenario: User downloads a large arXiv paper
- **Given** an authenticated user starts downloading an arXiv paper with multiple large files
- **When** the `DownloadProgressCallback` receives data chunks
- **Then** the backend must only perform a database update (via `task_manager.update_task`) when the integer percentage of the overall progress changes or the stage completes, rather than on every chunk.
- **And** the download speed must not be bottlenecked by database IO.

### Requirement: Premium UI display for download progress
The frontend MUST display an interactive and premium progress bar according to ui-ux-pro-max guidelines.

#### Scenario: User observes the arXiv download progress
- **Given** the frontend is displaying the download progress of an active task
- **When** the task is in `downloading`, `extracting`, `downloading_pdf`, or `validating` stage
- **Then** the progress bar must display an animated shimmer effect when not complete
- **And** the UI must show a pulsing dot, the current stage in English or localized language, and the numerical percentage.
- **And** the progress indicator must have smooth transition animations matching ui-ux-pro-max guidelines.

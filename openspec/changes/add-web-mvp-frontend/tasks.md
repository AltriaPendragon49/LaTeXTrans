# Implementation Tasks

## Prerequisites
**REQUIRED**: Backend change `add-web-mvp-platform` must be completed and running before starting these tasks. Verify backend API endpoints are accessible at http://localhost:8000.

## 1. Frontend Project Initialization
- [ ] 1.1 Create React app using Vite: `npm create vite@latest frontend -- --template react`
- [ ] 1.2 Install dependencies: `cd frontend && npm install`
- [ ] 1.3 Install Axios: `npm install axios`
- [ ] 1.4 Install TailwindCSS: `npm install -D tailwindcss postcss autoprefixer`
- [ ] 1.5 Initialize TailwindCSS configuration: `npx tailwindcss init -p`
- [ ] 1.6 Configure Tailwind in `src/index.css` (add directives)
- [ ] 1.7 Update `package.json` with project metadata

## 2. API Client Layer
- [ ] 2.1 Create `src/utils/api.js` with Axios instance
  - Base URL: `http://localhost:8000`
  - Configure timeout and error handling
- [ ] 2.2 Implement API methods:
  - `uploadFile(file)` → POST /upload
  - `submitArxivId(arxivId)` → POST /arxiv
  - `startTranslation(taskId)` → POST /translate/{taskId}
  - `getTaskStatus(taskId)` → GET /task/{taskId}
  - `downloadPDF(taskId)` → GET /download/{taskId}/pdf
  - `downloadSource(taskId)` → GET /download/{taskId}/source

## 3. UI Components Development
- [ ] 3.1 Create `src/components/FileUpload.jsx`
  - Drag-and-drop zone for `.tex` and `.zip` files
  - File validation (extension: `.tex`, `.zip`; size limit: 50MB)
  - Display selected file name and size
  - Upload progress indicator
  - Call `uploadFile()` API and store returned task ID
  - Error handling with user-friendly messages

- [ ] 3.2 Create `src/components/ArxivInput.jsx`
  - Text input with placeholder "e.g., 2508.18791"
  - Format validation (regex: `^\d{4}\.\d{4,5}$`)
  - Submit button with loading state
  - Call `submitArxivId()` API and store returned task ID
  - Display download status for arXiv fetch

- [ ] 3.3 Create `src/components/ProgressTracker.jsx`
  - Poll `getTaskStatus()` every 2 seconds when task is active
  - Progress bar (0-100%) with smooth transitions
  - Stage indicator: "Parsing" → "Translating" → "Compiling"
  - Current message display (e.g., "Processing section 3/10")
  - Error display with red alert styling
  - Auto-stop polling when status is "completed" or "failed"

- [ ] 3.4 Create `src/components/DownloadButton.jsx`
  - Conditionally render when task status is "completed"
  - "Download PDF" button → trigger `downloadPDF()`
  - "Download Source (.zip)" button → trigger `downloadSource()`
  - Handle file download via browser download mechanism
  - Loading states during download

- [ ] 3.5 Create `src/components/TabSwitcher.jsx`
  - Toggle between "Upload File" and "arXiv ID" modes
  - Active tab highlighting
  - Preserve state when switching tabs

## 4. Main Application Layout
- [ ] 4.1 Update `src/App.jsx` with main layout:
  - Header: Project title "LaTeXTrans-Pro" with logo
  - Tab switcher component
  - Left panel: FileUpload OR ArxivInput (based on active tab)
  - Right panel: ProgressTracker + DownloadButton
  - Responsive layout (mobile-friendly)

- [ ] 4.2 Implement state management:
  - Current task ID
  - Task status (pending, processing, completed, failed)
  - Active tab selection
  - Error messages

- [ ] 4.3 Apply TailwindCSS styling:
  - Modern, clean design with glassmorphism effects
  - Color scheme: Dark mode support
  - Smooth animations for state transitions
  - Accessible focus states and ARIA labels

## 5. Integration Testing
- [ ] 5.1 Test scenario: Upload simple `.tex` file
  - Select file via drag-and-drop
  - Verify file validation (accept .tex, reject .pdf)
  - Confirm upload initiates translation
  - Verify progress updates appear
  - Confirm PDF download works after completion

- [ ] 5.2 Test scenario: Enter arXiv ID (e.g., `2508.18791`)
  - Enter valid arXiv ID
  - Verify format validation
  - Confirm arXiv download triggers
  - Verify translation progress
  - Confirm PDF download works

- [ ] 5.3 Test scenario: Upload `.zip` with multiple files
  - Upload compressed archive
  - Verify extraction message appears
  - Confirm main file detection
  - Verify translation completes

- [ ] 5.4 Test error handling:
  - Invalid file format (e.g., `.pdf`)
  - File too large (>50MB)
  - Non-existent arXiv ID
  - Backend API unreachable
  - Translation failure (backend error)

- [ ] 5.5 Cross-browser testing:
  - Chrome (latest)
  - Firefox (latest)
  - Edge (latest)
  - Safari (if available)

- [ ] 5.6 Responsive design testing:
  - Desktop (1920x1080)
  - Laptop (1366x768)
  - Tablet (768x1024)
  - Mobile (375x667)

## 6. Documentation
- [ ] 6.1 Create `frontend/README.md`:
  - Prerequisites (Node.js 18+)
  - Installation instructions
  - Development server command: `npm run dev`
  - Build command: `npm run build`
  - Environment configuration (.env variables if needed)

- [ ] 6.2 Update main project `README.md`:
  - Add frontend setup section
  - Update Quick Start guide with frontend instructions
  - Add screenshots of web interface

- [ ] 6.3 Create troubleshooting guide:
  - Common CORS issues
  - Backend connection errors
  - File upload failures
  - Browser compatibility issues

## 7. Deployment Preparation
- [ ] 7.1 Create `frontend/start.sh` startup script:
  ```bash
  #!/bin/bash
  cd frontend
  npm install
  npm run dev
  ```

- [ ] 7.2 Verify production build:
  - Run `npm run build`
  - Test built files in `dist/`
  - Ensure build size is reasonable (<5MB)

- [ ] 7.3 Configure environment variables (if needed):
  - `VITE_API_BASE_URL` for backend endpoint
  - Create `.env.example` template

## Dependencies and Sequencing

**Critical Dependencies**:
- ❗ Backend API must be running and accessible before testing any frontend functionality
- ❗ All API endpoints from `add-web-mvp-platform` must be implemented and functional

**Recommended Order**:
1. Complete Section 1 (Project Init) first
2. Complete Section 2 (API Client) to establish backend connection
3. Build components in Section 3 in order (3.1 → 3.5)
4. Integrate in Section 4
5. Test thoroughly in Section 5
6. Document in Section 6

**Parallel Work**: 
- Components 3.1-3.5 can be developed in parallel if multiple developers are available
- Documentation (Section 6) can be written alongside development

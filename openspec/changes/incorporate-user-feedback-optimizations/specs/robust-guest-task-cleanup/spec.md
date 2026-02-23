## ADDED Requirements

### Requirement: Robust Temporary Task Cleanup
The system MUST accurately and persistently clean up temporary guest tasks and any orphaned output files to prevent storage leaks.

#### Scenario: Background cleanup removes old guest task
A guest task's output directory becomes older than the configured TTL (e.g., 2 hours). The background cleanup job runs, identifies the task ID from the directory name, and queries the database. Since the guest task does not exist in the database, the directory MUST be permanently deleted.

#### Scenario: Server restart does not orphan guest tasks
The backend server restarts. The in-memory guest task tracker is cleared. The background cleanup job runs, identifies old guest task directories on disk, confirms they are not in the database, and deletes them, ensuring no storage leak occurs across restarts.

#### Scenario: Cleanup removes deleted user tasks 
A registered user's task output directory exists, but the user manually deleted the task from the database. The background cleanup job identifies the inconsistency and deletes the orphaned output directory.

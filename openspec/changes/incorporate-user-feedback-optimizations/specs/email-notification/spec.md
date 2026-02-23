## ADDED Requirements

### Requirement: Task Completion Email Notification
The system MUST allow users to opt-in to receive an email notification upon the completion or failure of their translation tasks.

#### Scenario: User enables email notification
A user opens the Advanced Configuration dialog. They MUST see a toggle switch labeled "发送邮件通知 (完成时)". A user activates the email notification toggle and submits a task. The backend MUST record this preference in the task's `advanced_config`.

#### Scenario: Task completes and email is sent
A task with email notification enabled reaches the `COMPLETED` or `FAILED` state. The backend MUST use its internal SMTP `EmailService` to dispatch an email to the user indicating the final status of the task.

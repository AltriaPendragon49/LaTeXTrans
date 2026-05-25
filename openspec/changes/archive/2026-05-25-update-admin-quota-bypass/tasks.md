## 1. Implementation
- [x] 1.1 Add a shared admin-role check for local LaTeX quota bypass.
- [x] 1.2 Update single translation start to skip local quota reservation for admin users.
- [x] 1.3 Update batch arXiv and batch upload translation to skip local quota reservation/release for admin users.
- [x] 1.4 Update quota snapshot output so admin users are not shown as blocked by local daily LaTeX quota.
- [x] 1.5 Add or update backend tests for admin single translation, admin batch translation, admin batch upload, non-admin quota enforcement, and admin quota snapshot behavior.
- [x] 1.6 Run targeted backend tests and OpenSpec validation.

## 2. Deployment
- [ ] 2.1 Commit and push the approved implementation.
- [ ] 2.2 Pull the updated backend on the server and redeploy/restart the backend runtime.
- [ ] 2.3 Verify an admin account can start a translation with exhausted local daily quota.
- [ ] 2.4 Optionally reset the current admin user's MySQL `user_daily_quotas` row to restore 3 local quota items before deployment if immediate testing is needed.

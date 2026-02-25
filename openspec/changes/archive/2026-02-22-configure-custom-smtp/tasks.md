# Tasks

## 1. Documentation (OpenSpec Phase)
- [x] Create `proposal.md` with context and change scope.
- [x] Create `design.md` detailing SpaceMail SMTP configuration.
- [x] Create `specs/user-auth/spec.md` delta to update the registration email scenario to reflect reliable SMTP behavior without VPN.

## 2. Configuration & Implementation (Apply Phase)
- [x] Connect to the Supabase project dashboard.
- [x] Navigate to Authentication -> Emails -> SMTP settings.
- [x] Enable Custom SMTP and input corresponding Host, Port, Username, and Password for `tomato@latextrans.online`.
- [x] Save settings and perform a test email send to verify configuration.

## 3. Validation
- [x] Attempt a new user sign-up via the frontend or Supabase dashboard testing tool.
- [x] Verify that a confirmation email is successfully delivered without requiring VPN intervention.

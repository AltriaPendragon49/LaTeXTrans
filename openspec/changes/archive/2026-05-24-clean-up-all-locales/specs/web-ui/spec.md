## MODIFIED Requirements

### Requirement: User-visible static UI copy uses centralized i18n resources

All non-diagnostic user-visible frontend copy MUST come from centralized i18n resources instead of hardcoded strings, and each maintained locale MUST provide professional target-language copy without placeholder corruption.

#### Scenario: Main pages render localized UI copy
- **WHEN** the user visits the community homepage, paper detail, translation workspace, workspace history, workspace settings, workspace glossary, processing, preview, login, or profile
- **THEN** titles, buttons, descriptions, empty states, toast copy, and accessibility text MUST be resolved from locale resources
- **AND** changing the active UI language MUST update those strings consistently

#### Scenario: Maintained locales avoid placeholder corruption and unresolved prompt punctuation
- **WHEN** a maintained locale file under `frontend/src/locales/` is shipped
- **THEN** its user-visible strings MUST be written in the target locale language instead of unresolved English fallback
- **AND** it MUST NOT contain placeholder corruption such as `????`
- **AND** active UI prompts that were intentionally professionalized in this cleanup MUST NOT regress to stray half-width or full-width question-mark endings caused by translation fallout

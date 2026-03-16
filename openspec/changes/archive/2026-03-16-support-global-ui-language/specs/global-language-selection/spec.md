# global-language-selection Specification Delta

## ADDED Requirements

### Requirement: Users can switch the global UI language across all supported locales
The frontend MUST allow users to switch the application UI language between `en`, `zh`, `ja`, `ko`, `de`, `fr`, `es`, and `ru`, and MUST persist the selected language across reloads.

#### Scenario: Switching the UI language
- **WHEN** the user opens the global language selector from the application shell
- **THEN** the system MUST display all 8 supported UI languages
- **WHEN** the user selects a different language
- **THEN** the visible UI copy MUST update immediately without requiring a page refresh
- **AND** the preference MUST be restored on the next visit

### Requirement: The global language selector provides localized accessibility copy
The application shell MUST localize the selector label, related navigation labels, and accessibility text used by shell components.

#### Scenario: Shell a11y copy follows the active language
- **WHEN** the active UI language changes
- **THEN** the selector label, sidebar toggle label, sheet close label, and related accessible text MUST switch to the same language
- **AND** keyboard and screen-reader interaction MUST continue to work

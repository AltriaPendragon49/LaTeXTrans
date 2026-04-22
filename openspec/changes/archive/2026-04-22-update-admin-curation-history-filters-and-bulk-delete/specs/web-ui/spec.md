## ADDED Requirements
### Requirement: Admin curation history UI supports current-result bulk actions
The web UI SHALL let admins select multiple currently listed curation history records and batch hard-delete the selected set from the history page.

#### Scenario: Admin selects current filtered results
- **WHEN** an admin checks one or more task records in the history list
- **THEN** the page SHALL show the current selected count
- **AND** the page SHALL offer a select-all action for the currently listed filtered results only.

#### Scenario: Admin confirms batch delete
- **WHEN** an admin confirms batch delete for the current selection
- **THEN** the page SHALL call the batch delete API with the selected job ids
- **AND** successful deletions SHALL be removed from the current selection and refreshed result list
- **AND** failed deletions SHALL remain visible with an error message so the admin can retry or inspect them.

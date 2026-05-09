## ADDED Requirements
### Requirement: Admin Curation Translation Uses Origin CLI Parity
Admin and community curation translation tasks SHALL use the same origin CLI parity kernel as ordinary backend translation tasks.

#### Scenario: Admin arXiv curation starts parity translation
- **WHEN** an admin curation job starts translation from an arXiv id
- **THEN** the translation task SHALL use `origin_cli_parity`
- **AND** curation-specific timeout, retention, and publishing metadata SHALL NOT change the translation kernel.

#### Scenario: Admin archive curation starts parity translation
- **WHEN** an admin curation job starts translation from an uploaded archive
- **THEN** the translation task SHALL use `origin_cli_parity`
- **AND** curation-specific cost settings such as disabling terminology output SHALL NOT enable modern translation-kernel behavior.


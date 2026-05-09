## ADDED Requirements
### Requirement: Batch Translation Items Use Origin CLI Parity
Each item submitted through batch translation SHALL execute as an independent origin CLI parity task.

#### Scenario: Batch arXiv item uses parity
- **WHEN** a batch request enqueues an arXiv translation item
- **THEN** that item SHALL use the same `origin_cli_parity` task configuration as a single arXiv translation.

#### Scenario: Batch upload item uses parity
- **WHEN** a batch request enqueues an uploaded archive translation item
- **THEN** that item SHALL use the same `origin_cli_parity` task configuration as a single uploaded-file translation.


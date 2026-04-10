## ADDED Requirements
### Requirement: Include resolution skips directory targets safely
The system SHALL resolve `\input` and `\include` targets only to existing files, and it MUST NOT attempt to open directory-like targets as though they were `.tex` files.

#### Scenario: Parser encounters a directory target
- **WHEN** LaTeX merge or parser logic encounters `\input{figs/ablation}` or a similar include target whose resolved path is a directory rather than a file
- **THEN** the system SHALL treat that target as unresolved instead of opening it
- **AND** it SHALL continue parsing without raising `IsADirectoryError` or equivalent file-open failures

#### Scenario: Include resolution still honors explicit files
- **WHEN** an `\input` or `\include` target resolves to an existing file path directly or through an added `.tex` suffix
- **THEN** the system SHALL load that file normally
- **AND** the directory-skip guard SHALL NOT break healthy include resolution for valid files

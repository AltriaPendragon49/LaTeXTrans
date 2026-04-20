## MODIFIED Requirements
### Requirement: Prewarmed readable assets are immediately usable by the reader
The public and community reading experience SHALL immediately use prewarmed readable assets from the content pool when they already exist, instead of acting like the paper still needs to be translated live.

#### Scenario: Paper detail opens for a prewarmed translated paper
- **WHEN** a user opens a paper whose translated reader or translated preview was already produced by the content pool
- **THEN** the detail page SHALL use that translated-readable state immediately
- **AND** it SHALL not force the user through a fresh translation-start path for the same paper.

#### Scenario: Public translated PDF reads use a ready delivery asset
- **WHEN** a user opens or downloads a translated PDF for a public community paper
- **THEN** the public read path SHALL resolve an already-prepared canonical translated PDF delivery asset
- **AND** it SHALL not perform user-visible leading-blank-page trimming, heavy asset recovery, or full object-storage materialization before beginning delivery.

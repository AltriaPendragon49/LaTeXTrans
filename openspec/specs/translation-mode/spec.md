# translation-mode Specification

## Purpose
定义翻译模式规范，包括全文翻译和快速筛查模式的行为。
## Requirements
### Requirement: Full document translation only
The system SHALL translate the entire document by default. All sections, captions, and environments are translated.

#### Scenario: User translates a document
- **WHEN** user submits a LaTeX document for translation
- **THEN** all sections are translated
- **AND** all captions and environments are translated
- **AND** output PDF is compiled successfully

### Requirement: Error retry mechanism
The system SHALL retry failed translation segments using the errors_report data.

#### Scenario: Translation errors trigger retry
- **WHEN** translation has validation errors
- **AND** errors_report is not empty
- **THEN** TranslatorAgent retranslates failed parts
- **AND** retry count is limited to MAX_RETRIES (3)


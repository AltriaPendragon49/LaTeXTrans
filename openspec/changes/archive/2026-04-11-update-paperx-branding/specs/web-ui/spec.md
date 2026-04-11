## MODIFIED Requirements
### Requirement: Web UI Branding
The application MUST display professional PaperX branding across shared web shell surfaces, including a descriptive `<title>`, a unique favicon, and the shared navigation logo/name.

#### Scenario: Browser tab branding
- **WHEN** a user opens or bookmarks the website
- **THEN** they MUST see the PaperX application title and PaperX favicon in the browser tab.

#### Scenario: Shared shell branding
- **WHEN** a user views the shared application sidebar or tools workspace
- **THEN** the UI MUST display the PaperX brand name and configured PaperX logo asset instead of legacy LaTeXTrans naming.

#### Scenario: Locale-managed PaperX copy stays language-aligned
- **WHEN** PaperX branding or related community-reader copy is surfaced through locale files
- **THEN** each maintained locale MUST provide copy in its target language rather than leaving legacy source-language text, untranslated English fallback, or placeholder corruption such as question-mark strings.

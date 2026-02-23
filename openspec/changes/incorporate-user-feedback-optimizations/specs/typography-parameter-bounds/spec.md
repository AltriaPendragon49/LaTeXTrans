## ADDED Requirements

### Requirement: Typography Parameter Bounds Validation
The system MUST validate advanced typography parameters (font size, line spacing) to prevent invalid values that cause compilation errors or unreadable PDFs.

#### Scenario: User provides out-of-bounds parameters
A user enters a font size outside `[8, 14]` pt or line spacing outside `[1.0, 2.5]`. The backend MUST skip the application of these parameters and append a warning to the `fmt_warnings` list. The frontend MUST restrict numerical inputs to these ranges and provide tooltips explaining the limits.

## ADDED Requirements

### Requirement: Precompile Structure Validation Is Externally Visible
The system SHALL expose compile-time structure validation as a distinct precompile phase so operators and downstream UIs can distinguish structural checking from compile queue wait time.

#### Scenario: Structure validation status precedes compile queue waiting
- **WHEN** the generator locates the compile-ready `main.tex`
- **THEN** it MUST emit a dedicated status such as `Checking project structure...`
- **AND** this status MUST occur before any compile queue waiting message can be shown.

#### Scenario: Structure validation duration is recorded separately
- **WHEN** `validate_project_structure` executes during the compile pipeline
- **THEN** the system MUST record its execution duration in runtime logs or audit metrics
- **AND** the recorded duration MUST measure the validation call itself rather than surrounding compile execution time.

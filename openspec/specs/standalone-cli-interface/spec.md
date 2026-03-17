# standalone-cli-interface Specification

## Purpose
TBD - created by archiving change extract-standalone-cli-translation-core. Update Purpose after archive.
## Requirements
### Requirement: Legacy-Compatible CLI Entry
The standalone open-source package SHALL expose a prototype-style `main.py` command-line interface with compatible legacy flags.

#### Scenario: Running legacy-compatible CLI flags
- **WHEN** a user runs `python main.py --source <dir>` or `python main.py --arxiv <id>`
- **THEN** the command MUST be accepted by the standalone CLI
- **AND** the CLI MUST support legacy flags `--config`, `--model`, `--url`, `--key`, `--arxiv`, `--output`, and `--source`
- **AND** the CLI MAY also expose enhanced flags for language, compile strategy, translation mode, terminology generation, and log level.

### Requirement: CLI Configuration Precedence
The standalone CLI SHALL use deterministic configuration precedence.

#### Scenario: CLI overrides config file
- **WHEN** a setting is defined both in `config/default.toml` and via CLI flag
- **THEN** the CLI flag MUST take precedence
- **AND** TOML values MUST override code-level defaults.

### Requirement: CLI Output Contract
The standalone CLI SHALL emit prototype-style output directories while retaining current kernel diagnostics.

#### Scenario: Successful standalone translation
- **WHEN** a translation completes successfully
- **THEN** the translated project MUST be written under `outputs/<target_language>_<project_name>/`
- **AND** the compiled PDF MUST be written in that directory
- **AND** the system MUST persist `task_log.json` and `replay_bundle.json` alongside other translation artifacts.

### Requirement: Standalone Exit Codes
The standalone CLI SHALL return explicit process exit codes.

#### Scenario: CLI exits after translation run
- **WHEN** the CLI completes execution
- **THEN** it MUST return `0` for success
- **AND** MUST return `1` for translation or compilation failure
- **AND** MUST return `2` for input or configuration errors
- **AND** MUST return `3` for environment preparation failures.


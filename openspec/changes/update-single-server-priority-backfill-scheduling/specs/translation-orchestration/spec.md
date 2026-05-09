## MODIFIED Requirements
### Requirement: State-Machine Orchestration and Agent Scope
The system SHALL orchestrate parsing, translation, validation, and compilation exclusively through a LangGraph StateMachine, and any outer scheduler SHALL treat one paper run as an indivisible orchestration kernel rather than splitting LangGraph nodes across independent workers.

#### Scenario: LangGraph Agent Guardrails
- **WHEN** the agent handles orchestration across paragraphs, package conflicts, or layout logic
- **THEN** it operates within scope
- **AND** the system MUST PREVENT the agent from executing character-level syntax fixes or entering infinite retry cycles.

#### Scenario: Single-paper kernel remains intact under scheduler scaling
- **WHEN** the system adds queue priority, yielding, or token-pool scheduling
- **THEN** those controls MUST operate outside the LangGraph paper workflow
- **AND** the change MUST NOT distribute nodes from the same paper across multiple independent workers or queues.

#### Scenario: Cooperative yield occurs only at safe checkpoints
- **WHEN** the scheduler requests capacity from a running backfill task
- **THEN** the orchestrator MAY yield only after a completed checkpoint such as parse completion, section-batch flush, validation-round completion, pre-compile boundary, or post-compile boundary
- **AND** MUST persist enough checkpoint metadata to resume from that boundary
- **AND** MUST NOT yield mid-LLM request or mid-compile subprocess.

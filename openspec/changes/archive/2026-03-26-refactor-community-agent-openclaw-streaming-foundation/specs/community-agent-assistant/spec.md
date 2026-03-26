## MODIFIED Requirements
### Requirement: Agent translation starts with a visible but non-blocking progress model
The agent SHALL present translation as a visible, tool-style progress timeline without forcing the user through a confirmation-heavy workflow, and it SHALL treat translation startup as a background action that does not terminate the current answer.

#### Scenario: User starts translation from the community flow
- **WHEN** a user requests translation for a readable English paper
- **THEN** the system SHALL start the default community translation flow without asking for extra confirmation steps in normal cases
- **AND** it SHALL surface progress as timeline/status events rather than forcing the user into a separate operations-style workflow.

#### Scenario: Translation workflow remains available as a direct tool
- **WHEN** the agent can call the current translation workflow as a tool
- **THEN** the standalone translation UI SHALL still remain available for users who prefer the explicit workflow
- **AND** both surfaces SHALL map to the same underlying translation capability.

#### Scenario: Translation handoff does not terminate answer generation
- **WHEN** the runtime starts translation for a paper during a conversational run
- **THEN** it SHALL continue generating the current answer
- **AND** it SHALL surface translation progress as background status rather than ending the turn immediately.

### Requirement: Community agent runs as a conversational tool-calling assistant
The community agent SHALL use a conversational tool-calling runtime in which OpenClaw-style prompt skills guide behavior while executable tool schemas come from a separate tool registry, so the model can answer directly or call visible paper-domain tools before answering.

#### Scenario: Assistant answers directly after reading skill prompt and current paper context
- **WHEN** the user asks a question that the model can answer from the current conversation, current paper context, and loaded prompt skills without calling tools
- **THEN** the runtime SHALL accept the model’s natural-language assistant reply as the final answer
- **AND** it SHALL NOT require a slot-based `finalize` payload or a synthetic compose step.

#### Scenario: Assistant calls one or more visible tools before the final answer
- **WHEN** the model emits one or more tool calls for visible paper-domain tools
- **THEN** the runtime SHALL execute those tools, append the tool results back into the conversation, and continue the loop
- **AND** it SHALL finalize only after the model returns a natural-language assistant reply.

#### Scenario: Hidden tool remains uncallable even if a skill references it
- **WHEN** a prompt skill mentions a capability whose executable tool is not visible for the current run
- **THEN** the runtime SHALL keep that tool hidden from the model-facing tool registry
- **AND** any attempted call to that hidden tool SHALL be rejected and repaired or safely fall back.

## ADDED Requirements
### Requirement: Community agent uses OpenClaw-style prompt skills
The community agent SHALL load bundled `SKILL.md` instruction packs as prompt skills that guide reasoning and tool use, while keeping executable tool schemas, validation, and execution in a separate tool registry.

#### Scenario: Runtime loads bundled prompt skills
- **WHEN** a run starts
- **THEN** the runtime SHALL load eligible `SKILL.md` instructions as prompt skills
- **AND** it SHALL NOT expose markdown skill files themselves as executable tool schemas.

#### Scenario: Tool registry remains separate from skill prompt
- **WHEN** the model chooses a tool
- **THEN** tool validation and execution SHALL come from the tool registry
- **AND** skill markdown SHALL only guide tool selection and response behavior.

### Requirement: Community agent streams the final answer token by token
The community agent SHALL generate the final assistant answer through a streaming completion so the client can render incremental text while preserving language alignment and paper-aware answer quality.

#### Scenario: Final answer is streamed
- **WHEN** the runtime enters final answer generation
- **THEN** it SHALL request a streaming completion
- **AND** it SHALL emit incremental assistant text chunks to the client.

#### Scenario: User language remains aligned during streaming
- **WHEN** the detected response language is Chinese or another supported language
- **THEN** the streamed output SHALL stay in that language
- **AND** fallback and translation-status phrasing SHALL remain language-aligned.

### Requirement: Agent provides a fast first answer before full translation is ready
The community agent SHALL provide an immediate grounded first answer when a newly loaded paper still lacks translated reader-ready content, instead of waiting for the full translation kernel to finish.

#### Scenario: Newly imported paper has no translated abstract yet
- **WHEN** a newly imported or newly loaded paper lacks translated reader-ready content
- **THEN** the runtime SHALL still provide an immediate grounded first answer using available title and abstract evidence
- **AND** it SHALL not wait for the full translation kernel to finish before replying.

### Requirement: Explicit paper lookup bridges to translation when needed
The community agent SHALL bridge explicit arXiv-id and exact-title paper lookup hits into translation readiness checks, and SHALL auto-start translation when no translated-ready community version exists.

#### Scenario: User queries by arXiv id and translation is missing
- **WHEN** the user explicitly asks about a paper by arXiv id and the paper is found/imported but not translated-ready
- **THEN** the runtime SHALL read paper context and auto-start `start_translation_kernel`
- **AND** it SHALL continue the conversational answer in the same turn.

#### Scenario: User queries by exact title and translation is missing
- **WHEN** the user explicitly asks for a paper by exact title and a community hit is found but not translated-ready
- **THEN** the runtime SHALL read paper context for that hit and auto-start translation
- **AND** it SHALL emit action metadata containing `paper_id` and `task_id` for downstream UI navigation/progress.

#### Scenario: User queries by title and community has no paper yet
- **WHEN** the user explicitly asks for a paper by title and community search returns no hit
- **THEN** the runtime SHALL resolve the title against arXiv metadata, import the resolved paper, and read paper context
- **AND** it SHALL auto-start translation in the same run when the imported paper is not translated-ready.

### Requirement: Agent-triggered translation fails deterministically on backend restart
The community agent SHALL treat backend-restart interruption as a deterministic terminal failure so translation state is not left in an indeterminate in-progress state.

#### Scenario: Restart interrupts agent-started translation
- **WHEN** the agent has already started a background translation task for a paper and the backend restarts before completion
- **THEN** the system SHALL mark the interrupted task as `failed` during startup/admin reconciliation
- **AND** the paper SHALL not remain indefinitely stuck at queued/processing after restart.

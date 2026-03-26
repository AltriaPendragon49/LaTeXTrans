# community-agent-assistant Specification

## Purpose
TBD - created by archiving change refactor-community-agent-first-shell. Update Purpose after archive.
## Requirements
### Requirement: Community homepage uses an agent-first research entry
The community homepage SHALL prioritize a single centered agent-style input that infers user intent for paper search, paper explanation, or translation requests and acts as the primary first-screen surface.

#### Scenario: Homepage input infers paper search intent
- **WHEN** a user enters text that looks like a paper title, topic, keyword, or research area
- **THEN** the system SHALL treat the input as a paper discovery request by default
- **AND** the page SHALL NOT require the user to choose an explicit mode before searching in normal cases.

#### Scenario: Homepage input infers question intent
- **WHEN** a user enters text that looks like a question about a paper or topic
- **THEN** the system SHALL treat the input as an explanation request by default
- **AND** the resulting answer SHALL remain connected to discoverable paper sources rather than behaving like a detached generic chatbot.

#### Scenario: Homepage input infers translation intent
- **WHEN** a user enters an arXiv identifier, arXiv URL, or a translation-like instruction
- **THEN** the system SHALL treat the input as a translation-oriented request by default
- **AND** the user SHALL NOT need to navigate to the legacy translation workspace first.

### Requirement: Agent conversations continue in a dedicated workspace
The community agent SHALL move long-lived interaction into a dedicated conversation workspace after the first submit rather than overloading the homepage with transcript state.

#### Scenario: First submit opens a dedicated conversation page
- **WHEN** a user submits a homepage prompt
- **THEN** the product SHALL open a dedicated agent conversation route
- **AND** the user SHALL continue the interaction there instead of staying in a homepage-only transcript shell.

#### Scenario: Logged-in users see saved conversation history
- **WHEN** an authenticated user has prior agent conversations
- **THEN** the dedicated conversation workspace SHALL show a saved conversation list
- **AND** starting a new chat SHALL create a new saved record tied to that user context.

### Requirement: Agent silently reuses or imports external papers when needed
The agent SHALL reuse existing community papers or silently import external arXiv papers into the community reading flow without extra confirmation clicks in normal healthy cases.

#### Scenario: External paper already exists in the community
- **WHEN** a user selects an external arXiv result whose paper already exists in the community
- **THEN** the system SHALL route the user directly to the existing community paper detail page
- **AND** it SHALL NOT ask for a redundant import confirmation.

#### Scenario: External paper is new to the community
- **WHEN** a user selects an external arXiv result whose paper is not yet present in the community
- **THEN** the system SHALL silently import or create the paper in the community flow
- **AND** it SHALL continue into a community detail page rather than leaving the user in an external-only browsing state.

### Requirement: Agent answers emphasize paper understanding before tool detail
The community agent SHALL present a paper-oriented answer shape that prioritizes understanding the paper over displaying tool internals.

#### Scenario: User asks what a paper is about
- **WHEN** a user asks for the gist, contributions, or key findings of a paper
- **THEN** the answer SHALL lead with a concise paper overview and core points
- **AND** tool traces SHALL remain secondary supporting detail rather than the primary answer surface.

### Requirement: Agent behaves as a paper-domain multi-turn chat assistant
The community agent SHALL preserve multi-turn conversation context and keep follow-up answers grounded in the current paper or retrieved paper set rather than drifting into a generic assistant mode.

#### Scenario: User asks a follow-up question in the same conversation
- **WHEN** a user continues a conversation with follow-up prompts such as asking for details, comparisons, or translation after a previous paper-oriented answer
- **THEN** the system SHALL include relevant recent conversation context in the next agent run
- **AND** the answer SHALL remain anchored to the active paper thread or retrieved paper set.

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

### Requirement: Community agent only exposes currently visible tools
The community agent SHALL expose only currently visible tool schemas to the model and SHALL reject attempts to call hidden tools.

#### Scenario: External search tool hidden by user toggle
- **WHEN** a run is created with `skill_toggles.external_search=false`
- **THEN** the runtime MUST NOT expose `external_tavily_search` to the model
- **AND** any attempted call to that tool SHALL be rejected and repaired or safely fall back.

### Requirement: Community agent keeps conversational output aligned with the user language
The community agent SHALL return a natural assistant message in the user’s preferred language instead of forcing structured summary sections.

#### Scenario: Chinese prompt yields Chinese conversational answer
- **WHEN** the user asks a question in Chinese
- **THEN** the final assistant message SHALL be written in Chinese
- **AND** fallback copy, tool-driven answers, and paper-action guidance SHALL also remain in Chinese.

### Requirement: Community agent preserves paper-aware orchestration in the conversational loop
The community agent SHALL keep paper-domain automation such as arXiv import, paper-context loading, and translation handoff available inside the new conversational runtime.

#### Scenario: Missing arXiv paper is imported before grounded answer
- **WHEN** the user asks about an arXiv paper that is not yet available in the community workspace
- **THEN** the runtime SHALL import or reuse that paper and read its paper context before presenting a grounded answer.

#### Scenario: Imported paper still needs translation
- **WHEN** the runtime imports or reuses an arXiv-backed paper whose translated reader content is not ready and the user’s request implies translated reading support
- **THEN** it SHALL start the translation kernel automatically
- **AND** it SHALL return a consistent paper navigation action that the UI can surface.

### Requirement: Community agent validates search-oriented tool arguments
The community agent SHALL validate tool arguments for search-oriented skills so the model does not pass low-quality raw conversational filler into search backends.

#### Scenario: Search tool copies the raw utterance verbatim
- **WHEN** the model attempts to call an internal or external search skill using the raw conversational utterance as the query
- **THEN** the runtime SHALL reject that tool call
- **AND** it SHALL repair the turn or fall back rather than executing the low-quality search.

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

### Requirement: Community agent prefers prewarmed translated evidence when available
The community agent SHALL prefer prewarmed translated evidence from the community content pool before starting new on-demand translation work for the same paper.

#### Scenario: Internal search finds a prewarmed translated paper
- **WHEN** the agent retrieves a relevant community paper whose translated evidence is already available
- **THEN** it SHALL ground the answer on that prewarmed translated evidence first
- **AND** it SHALL avoid starting redundant translation work for the same paper in that turn.

#### Scenario: Content pool miss falls back to on-demand import and translation
- **WHEN** the agent cannot find suitable prewarmed translated evidence for the requested paper
- **THEN** it SHALL continue to use the existing on-demand import and translation fallback behavior
- **AND** the absence of a content-pool hit SHALL not block the conversation.

### Requirement: Community agent supports an explicit deep research mode
The community agent SHALL support an explicit deep research mode that expands retrieval breadth and produces a long-form cited synthesis without changing the default fast chat behavior.

#### Scenario: User chooses deep research mode
- **WHEN** the user explicitly starts a deep research run
- **THEN** the agent SHALL use a research-oriented retrieval and synthesis path
- **AND** the default chat mode SHALL remain available for normal paper questions.

#### Scenario: Deep research run prefers grounded multi-paper synthesis
- **WHEN** the agent completes a deep research run
- **THEN** the result SHALL synthesize multiple papers with citations
- **AND** it SHALL not degrade into a short single-paper chat answer unless the evidence set itself was too narrow.


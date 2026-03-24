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
The agent SHALL present translation as a visible, tool-style progress timeline without forcing the user through a confirmation-heavy workflow.

#### Scenario: User starts translation from the community flow
- **WHEN** a user requests translation for a readable English paper
- **THEN** the system SHALL start the default community translation flow without asking for extra confirmation steps in normal cases
- **AND** it SHALL surface progress as timeline/status events rather than forcing the user into a separate operations-style workflow.

#### Scenario: Translation workflow remains available as a direct tool
- **WHEN** the agent can call the current translation workflow as a tool
- **THEN** the standalone translation UI SHALL still remain available for users who prefer the explicit workflow
- **AND** both surfaces SHALL map to the same underlying translation capability.

### Requirement: Community agent runs as a conversational tool-calling assistant
The community agent SHALL use a conversational tool-calling runtime so the model can either answer naturally or call visible paper-domain tools before answering.

#### Scenario: Assistant answers directly without tools
- **WHEN** the user asks a question that the model can answer from the current conversation and available paper context without calling tools
- **THEN** the runtime SHALL accept the model’s natural-language assistant reply as the final answer
- **AND** it SHALL NOT require a slot-based `finalize` payload or a synthetic compose step.

#### Scenario: Assistant calls a visible tool before answering
- **WHEN** the model emits a tool call for a visible paper-domain skill
- **THEN** the runtime SHALL execute that skill, append the tool result back into the conversation, and continue the loop
- **AND** it SHALL finalize only after the model returns a natural-language assistant reply.

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


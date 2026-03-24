## ADDED Requirements

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

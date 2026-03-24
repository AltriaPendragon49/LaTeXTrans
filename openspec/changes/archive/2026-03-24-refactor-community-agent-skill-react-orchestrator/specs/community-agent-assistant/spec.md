## ADDED Requirements

### Requirement: Community agent uses visible typed skills for runtime orchestration
The community agent SHALL expose paper-agent capabilities as typed skills and only present currently visible skills to the planner model for each reasoning turn.

#### Scenario: External search skill hidden by user toggle
- **WHEN** a user submits a request with `skill_toggles.external_search=false`
- **THEN** the planner MUST NOT receive the `external_tavily_search` skill schema
- **AND** the runtime SHALL reject any attempted call to that hidden skill
- **AND** the runtime SHALL allow one repair cycle before falling back safely.

#### Scenario: Translation remains coarse-grained
- **WHEN** the planner needs to start translation
- **THEN** it SHALL call a single top-level `start_translation_kernel` skill
- **AND** the runtime SHALL NOT expose internal translation-kernel substeps as community-agent-callable skills.

### Requirement: Community agent final output is slot-based and formatter-rendered
The community agent SHALL require the planner to emit slot data instead of raw long-form answer text and SHALL render the final user-visible answer via a deterministic formatter.

#### Scenario: Planner tries to emit raw long-form finalize text
- **WHEN** the planner returns a finalize payload containing forbidden long-form answer text
- **THEN** the runtime SHALL reject the finalize payload
- **AND** it SHALL request one repair response before falling back.

#### Scenario: Generation is traced as an explicit skill
- **WHEN** the runtime generates the grounded background explanation or answer
- **THEN** it SHALL execute `compose_academic_answer`
- **AND** the run trace SHALL include that generation skill as a visible tool step.

### Requirement: Community agent validates intent, action, and evidence consistency
The community agent SHALL validate that its final intent, action, and citations are consistent with the executed skill results before returning a deliverable answer.

#### Scenario: Translation action inconsistent with executed skills
- **WHEN** the finalize payload claims a translation navigation action without a successful translation skill result
- **THEN** the runtime SHALL reject the finalize payload
- **AND** after one failed repair it SHALL return a fallback answer with no invalid action.

#### Scenario: Search query extraction is low quality
- **WHEN** a search skill call copies the raw conversational utterance instead of a normalized query
- **THEN** the runtime SHALL reject the skill arguments as low quality
- **AND** it SHALL require a repair or fallback rather than executing the low-quality query.

### Requirement: Community agent answer language follows the user's prompt language
The community agent SHALL infer the user's preferred response language from the latest prompt and keep planner prompts, composer output slots, formatter headings, and deterministic fallback text aligned with that language.

#### Scenario: Chinese question yields Chinese answer
- **WHEN** the user asks the community agent a question in Chinese
- **THEN** the planner/composer prompts SHALL explicitly steer the answer language to Chinese
- **AND** formatter headings, fallback summaries, and status text SHALL also be rendered in Chinese instead of defaulting to English.

### Requirement: Community agent auto-imports and prepares missing arXiv papers
The community agent SHALL bring missing arXiv papers into the community workspace before answering paper-specific questions and SHALL kick off translation when that imported paper still needs a translated reading asset.

#### Scenario: arXiv paper is missing from community
- **WHEN** the user asks about a specific arXiv paper that is not yet in the community workspace
- **THEN** the runtime SHALL import or reuse that paper first
- **AND** it SHALL read the imported paper context before composing the answer.

#### Scenario: arXiv id is adjacent to Chinese text
- **WHEN** the user asks about a specific arXiv paper with the identifier directly adjacent to Chinese text, such as `2602.24209讲了什么` or `请解释2602.24209这篇论文`
- **THEN** the runtime SHALL still extract the arXiv id correctly
- **AND** it SHALL trigger the same import/reuse and paper-context loading flow as other explicit arXiv-id questions instead of falling back as if no paper id was provided.

#### Scenario: imported arXiv paper still needs translation
- **WHEN** the runtime imports or reuses an arXiv-backed paper whose translated reader content is not ready
- **THEN** it SHALL start the translation kernel automatically
- **AND** any returned navigation action SHALL remain consistent with the executed import and translation steps.

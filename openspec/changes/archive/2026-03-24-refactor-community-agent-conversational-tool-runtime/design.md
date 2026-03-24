# Overview
This change moves the community paper assistant from a planner/finalize JSON state machine to a conversational tool-calling runtime.

The new runtime behaves like a normal chat assistant:
1. It receives the user message, short conversation history, optional paper context, and visible tool schemas.
2. The model can either answer directly in natural language or request one or more tool calls.
3. The runtime executes tool calls, appends structured tool results, and asks the model for the next assistant turn.
4. The loop ends when the model returns natural-language content.
5. The runtime returns the assistant message together with citations, tool trace, provider state, and optional paper navigation action.

## Goals
- Make the primary answer path conversational instead of slot-based.
- Reuse the existing domain skills as tools rather than forcing generation through a fake compose skill.
- Preserve language alignment, traceability, grounded evidence, and paper-domain actions.
- Keep a deterministic fallback path when tool calling or provider connectivity is unavailable.

## Non-Goals
- This change does not introduce multi-agent delegation or nested agent swarms.
- This change does not require streaming tokens in v1.
- This change does not remove backward compatibility fields immediately if the frontend or stored turns still reference them.

## Runtime Design
### Tool registry
The existing skill registry remains the single source of truth for visibility and schemas.

Visible conversational tools in v1:
- `community_search_papers`
- `external_tavily_search`
- `read_paper_context`
- `import_arxiv_paper`
- `start_translation_kernel`

`compose_academic_answer` remains in code only as a compatibility artifact if needed, but it is not part of the primary conversational loop.

### Prompting
The system prompt instructs the model to:
- answer conversationally in the user’s language
- use tools only when they improve correctness or complete a paper-domain action
- prefer community paper search/context before external search
- ground claims in returned tool evidence
- avoid inventing paper metadata or citations

### Tool calling
The runtime calls an OpenAI-compatible `/chat/completions` endpoint with:
- `messages`
- `tools`
- `tool_choice: "auto"`
- `temperature`

If the assistant returns `tool_calls`, the runtime:
- validates visibility and arguments
- executes each skill
- records `tool_trace` / `events`
- merges citations/action/paper context into runtime state
- appends tool results back into the conversation

If the assistant returns content without tool calls, the runtime finalizes with that natural-language assistant message.

### Fallback path
When tool-calling LLM access is unavailable or the loop fails validation:
- the runtime uses a small deterministic paper-aware fallback path
- fallback may still auto-import arXiv ids, read paper context, and start translation where appropriate
- fallback always returns a normal assistant message in the detected user language

## API Contract
`POST /api/community-agent/runs` returns:
- `message`: the natural assistant reply
- `summary`: deprecated compatibility alias equal to `message`
- `citations`
- `tool_trace`
- `provider_state`
- `action`

## UI Contract
The conversation page renders the assistant message as a normal chat bubble/body.
Structured metadata such as citations, tool trace, and paper action remain visible, but they are no longer reconstructed from hard-coded “Conclusion / Core points / Next steps” section markers.

## Testing Strategy
- Backend unit tests for:
  - direct natural-language completion
  - tool-call loop execution
  - visibility rejection for hidden tools
  - arXiv import/read-context fallback
  - language-aligned fallback copy
- Frontend unit tests for:
  - natural assistant message rendering
  - removal of structured summary section cards
  - preserved citations/action/tool trace rendering
- Acceptance:
  - `openspec validate refactor-community-agent-conversational-tool-runtime --strict --no-interactive`
  - targeted pytest and vitest suites
  - browser acceptance against local app

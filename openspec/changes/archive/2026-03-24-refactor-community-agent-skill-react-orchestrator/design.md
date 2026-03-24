# Overview
This change refactors the community paper agent into a typed orchestration runtime inspired by OpenClaw's visible-tool pattern:

1. The planner model only sees schemas for currently visible skills.
2. The model chooses a skill and extracts normalized arguments.
3. The runtime executes the skill and records a structured observation.
4. The model may iterate through more skill calls.
5. The runtime requires a slot-based `finalize` object instead of raw prose.
6. A deterministic formatter renders the final long-form answer from slots.
7. A validator checks consistency between the final answer, the executed skills, and the collected citations/actions.

# Runtime Model
## Request normalization
- Route layer accepts `skill_toggles.external_search`.
- Service façade normalizes `input`, `context`, `paper_id`, and `skill_toggles`.
- Runtime initializes provider state and a visibility-aware skill registry.

## Skill registry
Every skill exposes:
- `name`
- `description`
- `input_schema()`
- `output_schema()`
- `is_visible(runtime_state)`
- `execute(arguments, runtime_state)`

Visible v1 skills:
- `community_search_papers`
- `external_tavily_search`
- `read_paper_context`
- `import_arxiv_paper`
- `start_translation_kernel`
- `compose_academic_answer`

## Planner protocol
Each planner turn returns strict JSON:

```json
{
  "mode": "call_skill | finalize",
  "intent": "search | answer | translate",
  "skill_name": "optional when call_skill",
  "arguments": {},
  "slots": {
    "current_status": "",
    "background_answer": "",
    "paper_overview": "",
    "core_points": [],
    "next_steps": []
  },
  "citation_ids": [],
  "action": null,
  "self_check": ""
}
```

Restrictions:
- `finalize` must not contain raw long-form answer text.
- `compose_academic_answer` is the only generation skill that can emit answer slots.
- The formatter is solely responsible for rendering the long-form `summary`.

# Validation Model
## Structural validation
- hidden skill calls are rejected
- malformed args are rejected
- `finalize.summary` or other long-form free-text answer fields are rejected
- unknown `citation_ids` are rejected
- invalid `navigate_paper` actions are rejected

## Consistency validation
- translation action requires a successful `start_translation_kernel` result
- non-translation intents cannot fabricate translation actions
- action `paper_id` must match executed skill results
- external-search-based claims require an executed visible external search skill
- search query extraction is rejected when the query is a low-quality copy of the whole utterance

## Repair policy
- one repair attempt is allowed after validator feedback
- if repair still fails, runtime falls back to a safe formatter-generated answer with no invalid action/citations

# Tavily integration
- Use `COMMUNITY_AGENT_TAVILY_API_KEY`
- Use `COMMUNITY_AGENT_TAVILY_BASE_URL`, defaulting to `https://api.tavily.com`
- Call `POST /search`
- Disable Tavily answer generation because the community agent owns answer composition
- Normalize Tavily results into citation-ready items before handing evidence back to the planner / formatter

# Frontend compatibility
- The summary formatter preserves current section-oriented display while adding `Background / Answer`.
- `CommunityFeed` and `CommunityConversation` get a non-persistent toggle for `external_search`.
- `PaperDetail` is unchanged.

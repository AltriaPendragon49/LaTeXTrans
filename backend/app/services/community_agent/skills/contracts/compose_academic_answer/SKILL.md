---
name: compose_academic_answer
description: Generate grounded academic answer slots from the executed evidence.
---

# Compose Academic Answer Skill

## Contract
```json
{
  "kind": "community-agent-skill",
  "purpose": "Turn executed evidence into grounded answer slots before finalize.",
  "consumers": ["community-react-agent-planner", "community-react-agent-runtime"],
  "visibility": {
    "type": "always",
    "reason": "All non-error completions require grounded slot generation."
  },
  "trace": {
    "kind": "reasoning",
    "label": "Compose academic answer",
    "provider": "compose_academic_answer"
  }
}
```

## Input Schema
```json
{
  "type": "object",
  "properties": {
    "intent": {
      "type": "string",
      "enum": ["search", "answer", "translate"]
    },
    "user_input": { "type": "string" },
    "history_summary": { "type": "string" },
    "paper_context": { "type": "object" },
    "evidence_citation_ids": {
      "type": "array",
      "items": { "type": "string" }
    },
    "action_context": { "type": "object" }
  },
  "required": ["intent", "user_input", "evidence_citation_ids"]
}
```

## Output Schema
```json
{
  "type": "object",
  "properties": {
    "slots": {
      "type": "object",
      "properties": {
        "current_status": { "type": "string" },
        "background_answer": { "type": "string" },
        "paper_overview": { "type": "string" },
        "core_points": {
          "type": "array",
          "items": { "type": "string" }
        },
        "next_steps": {
          "type": "array",
          "items": { "type": "string" }
        }
      },
      "required": [
        "current_status",
        "background_answer",
        "core_points",
        "next_steps"
      ]
    },
    "citation_ids": {
      "type": "array",
      "items": { "type": "string" }
    }
  },
  "required": ["slots", "citation_ids"]
}
```

## Planner Notes
Use this skill before `finalize`.
This skill must ground its slots in executed evidence only.
Do not produce final long-form prose here; the formatter will render the final user-visible answer.

---
name: read_paper_context
description: Load current community paper context when a paper id is available.
---

# Read Paper Context Skill

## Contract
```json
{
  "kind": "community-agent-skill",
  "purpose": "Load the current community paper context so later reasoning and actions can ground on the selected paper.",
  "consumers": ["community-react-agent-planner", "community-react-agent-runtime"],
  "visibility": {
    "type": "conditional",
    "condition": "paper_id is already known in runtime context or can be inferred from previous skill results"
  },
  "trace": {
    "kind": "context",
    "label": "Current paper context",
    "provider": "read_paper_context"
  }
}
```

## Input Schema
```json
{
  "type": "object",
  "properties": {
    "paper_id": {
      "type": "string"
    }
  },
  "required": ["paper_id"]
}
```

## Output Schema
```json
{
  "type": "object",
  "properties": {
    "paper_id": { "type": ["string", "null"] },
    "title": { "type": "string" },
    "arxiv_id": { "type": ["string", "null"] },
    "abstract_raw": { "type": "string" },
    "abstract_translated": { "type": "string" },
    "trans_status": { "type": ["string", "null"] }
  }
}
```

## Planner Notes
Use this skill when the agent already knows the target `paper_id` and needs grounded paper context before answering, navigating, or translating.

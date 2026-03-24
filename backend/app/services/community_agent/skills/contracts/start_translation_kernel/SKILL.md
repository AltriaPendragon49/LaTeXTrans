---
name: start_translation_kernel
description: Start the full paper translation kernel for a community paper.
---

# Start Translation Kernel Skill

## Contract
```json
{
  "kind": "community-agent-skill",
  "purpose": "Start the full translation kernel for a known community paper as one atomic action.",
  "consumers": ["community-react-agent-planner", "community-react-agent-runtime"],
  "visibility": {
    "type": "always",
    "reason": "The translation kernel can be started whenever a valid paper_id is known."
  },
  "trace": {
    "kind": "translation",
    "label": "Translation kernel",
    "provider": "start_translation_kernel"
  }
}
```

## Input Schema
```json
{
  "type": "object",
  "properties": {
    "paper_id": { "type": "string" },
    "source_language": { "type": "string", "default": "en" },
    "target_language": { "type": "string", "default": "zh" }
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
    "task_id": { "type": ["string", "null"] },
    "status": { "type": ["string", "null"] },
    "reused_existing_task": { "type": "boolean" },
    "processing_url": { "type": ["string", "null"] }
  }
}
```

## Planner Notes
This is the only translation skill exposed to the community agent.
Do not attempt to decompose translation into internal translator, compiler, or validator substeps.

---
name: import_arxiv_paper
description: Import or reuse a paper by arXiv identifier.
---

# Import arXiv Paper Skill

## Contract
```json
{
  "kind": "community-agent-skill",
  "purpose": "Import a paper from arXiv into the community workspace or reuse an existing imported copy.",
  "consumers": ["community-react-agent-planner", "community-react-agent-runtime"],
  "visibility": {
    "type": "always",
    "reason": "Import/reuse by arXiv id is always available."
  },
  "trace": {
    "kind": "import",
    "label": "Silent arXiv import",
    "provider": "import_arxiv_paper"
  }
}
```

## Input Schema
```json
{
  "type": "object",
  "properties": {
    "arxiv_id": {
      "type": "string"
    }
  },
  "required": ["arxiv_id"]
}
```

## Output Schema
```json
{
  "type": "object",
  "properties": {
    "paper_id": { "type": ["string", "null"] },
    "reused": { "type": "boolean" },
    "imported": { "type": "boolean" }
  }
}
```

## Planner Notes
Use this skill when the user request or prior search results contain an arXiv identifier and the paper must be brought into the community workspace before reading or translation.

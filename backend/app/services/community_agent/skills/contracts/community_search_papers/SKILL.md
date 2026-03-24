---
name: community_search_papers
description: Search existing community papers using a normalized academic query.
---

# Community Search Papers Skill

## Contract
```json
{
  "kind": "community-agent-skill",
  "purpose": "Search the internal community paper index for citation-ready paper matches.",
  "consumers": ["community-react-agent-planner", "community-react-agent-runtime"],
  "visibility": {
    "type": "always",
    "reason": "Internal community paper search is always available."
  },
  "trace": {
    "kind": "search",
    "label": "Community paper search",
    "provider": "community_search_papers"
  }
}
```

## Input Schema
```json
{
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "description": "A normalized academic search query without conversational filler."
    },
    "limit": {
      "type": "integer",
      "minimum": 1,
      "maximum": 5,
      "default": 4
    }
  },
  "required": ["query"]
}
```

## Output Schema
```json
{
  "type": "object",
  "properties": {
    "query_executed": {
      "type": "string"
    },
    "results": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": { "type": "string" },
          "title": { "type": "string" },
          "url": { "type": ["string", "null"] },
          "source": { "type": "string" },
          "arxiv_id": { "type": ["string", "null"] },
          "paper_id": { "type": ["string", "null"] },
          "snippet": { "type": "string" }
        }
      }
    },
    "count": {
      "type": "integer"
    }
  }
}
```

## Planner Notes
Use this skill for internal paper retrieval before external search when the user asks for paper discovery, comparison, explanation, or paper-specific grounding.
Extract a concise academic query; do not pass raw filler like “please search” or “请帮我查一下”.

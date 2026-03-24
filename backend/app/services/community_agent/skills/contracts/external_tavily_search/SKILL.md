---
name: external_tavily_search
description: Search the external web for paper-relevant evidence using Tavily.
---

# External Tavily Search Skill

## Contract
```json
{
  "kind": "community-agent-skill",
  "purpose": "Search external web sources for paper-relevant evidence when the user explicitly enabled external search.",
  "consumers": ["community-react-agent-planner", "community-react-agent-runtime"],
  "visibility": {
    "type": "toggle",
    "toggle": "external_search",
    "reason": "External web search must be explicitly enabled by the user."
  },
  "trace": {
    "kind": "search",
    "label": "External Tavily search",
    "provider": "external_tavily_search"
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
      "description": "A normalized web-search query extracted from the user request."
    },
    "topic": {
      "type": "string",
      "enum": ["general", "news", "finance"],
      "default": "general"
    },
    "search_depth": {
      "type": "string",
      "enum": ["basic", "advanced"],
      "default": "basic"
    },
    "time_range": {
      "type": "string",
      "enum": ["day", "week", "month", "year"]
    },
    "max_results": {
      "type": "integer",
      "minimum": 1,
      "maximum": 5,
      "default": 4
    },
    "include_domains": {
      "type": "array",
      "items": { "type": "string" }
    },
    "exclude_domains": {
      "type": "array",
      "items": { "type": "string" }
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
    "provider": { "type": "string" },
    "query_executed": { "type": "string" },
    "request_id": { "type": ["string", "null"] },
    "response_time": { "type": ["number", "null"] },
    "usage_credits": { "type": ["number", "null"] },
    "results": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": { "type": "string" },
          "title": { "type": "string" },
          "url": { "type": ["string", "null"] },
          "snippet": { "type": "string" },
          "score": { "type": ["number", "null"] },
          "source": { "type": "string" },
          "favicon": { "type": ["string", "null"] }
        }
      }
    }
  }
}
```

## Planner Notes
Use this skill only when external search is visible.
You are responsible for extracting search strategy and constraints yourself: query, time range, include/exclude domains, and result count.
Do not pass the raw conversational utterance unchanged.

# Change: Add community agent deep research mode

## Why
- The current community agent is optimized for conversational paper help, not for broad-scope literature review across many papers.
- Current retrieval defaults are intentionally small, which protects the base chat path but prevents serious multi-document synthesis.
- We need a dedicated deep research mode that can expand recall, spend more time on evidence gathering, and deliver a long-form cited research brief without overloading the default chat experience.

## What Changes
- Add an explicit deep research mode for the community agent that uses expanded retrieval and long-form cited synthesis.
- Define a higher-recall retrieval plan that can gather approximately 15–20 relevant papers or evidence items for one research brief.
- Define async progress and final output behavior for long-running deep research jobs.
- Define the report contract for a long-form, citation-rich literature review rendered inside the community experience.

## Impact
- Affected specs:
  - `community-agent-assistant`
  - `web-api`
  - `web-ui`
  - new capability `community-deep-research`
- Depends on:
  - `refactor-community-agent-openclaw-streaming-foundation` for async/streaming foundations
- Benefits from:
  - `add-community-agent-content-pool-foundation` for higher-quality internal evidence
- Follow-up changes required later:
  - export/share workflows for deep research reports
  - richer note taking and citation management

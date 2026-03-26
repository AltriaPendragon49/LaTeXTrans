## Context
- The base community agent experience intentionally uses small retrieval limits and concise conversational answers.
- The requested deep research direction is a distinct mode, not a default expansion of every normal chat turn.
- This mode needs broader retrieval, longer synthesis time, and more structured output than the everyday paper copilot path.

## Goals / Non-Goals
- Goals:
  - Add an explicit deep research mode for multi-paper synthesis.
  - Expand retrieval to a materially larger evidence set than the default chat path.
  - Produce a long-form cited research brief rather than a short assistant answer.
  - Keep the default chat mode fast and lightweight.
- Non-Goals:
  - Do not turn every chat request into a deep research run.
  - Do not require arbitrary open-web browsing by default in this change.
  - Do not implement export, collaboration, or publication workflows in this change.

## Decisions
- Decision: Deep research is an explicit mode, not an automatic escalation.
  - Users must opt into a deep research run through a clear mode selection or dedicated action.
  - Normal chat remains optimized for fast, lightweight answers.

- Decision: Deep research uses expanded retrieval breadth.
  - A single deep research run may retrieve roughly 15–20 relevant papers or evidence items.
  - Internal community evidence is preferred first, and external retrieval remains optional or policy-bounded where enabled.

- Decision: Deep research is async-first.
  - Because retrieval breadth and synthesis length are materially larger than normal chat, the system treats deep research as a long-running async task with progress updates.
  - The user should still receive progressive status and partial visibility into stage progress where available.

- Decision: Final output is a long-form cited report.
  - The result is a report-length Markdown answer with section structure, explicit citation markers, and synthesis across multiple papers.
  - The report should be materially longer and more comprehensive than the default chat answer path.

- Decision: Retrieval and synthesis limits remain bounded.
  - The system sets an explicit upper bound on recall count, synthesis context packing, and runtime duration so a single deep research run cannot expand without control.
  - Partial evidence is acceptable when the run explains its coverage limits instead of pretending to be exhaustive.

## Risks / Trade-offs
- Higher recall and longer synthesis cost more latency and model budget than default chat.
- Large evidence sets can reduce answer quality if filtering and citation discipline are weak.
- Deep research mode can confuse users if it is not clearly distinguished from default chat.

## Migration Plan
1. Add the deep research mode contract on top of the streaming foundation.
2. Introduce bounded retrieval and progress states before tuning report length.
3. Render the report inside the community UI with explicit citation affordances.
4. Expand export and collaboration only in later changes.

## Open Questions
- None for this change. Export, collaboration, and publication workflows are deferred.

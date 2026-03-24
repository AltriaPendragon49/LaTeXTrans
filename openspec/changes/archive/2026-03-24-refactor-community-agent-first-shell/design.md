# Overview

This change keeps the current real provider-backed community agent baseline, then finishes the missing product shell around it so the experience behaves like an agent-first paper workspace rather than a demo card inside a feed page.

## Goals

- Keep the current provider-backed agent orchestration as the baseline.
- Move long-lived interaction into a dedicated conversation workspace.
- Persist conversation history in a user-scoped way.
- Present paper answers in a more paper-native format.
- Recover translated reading artifacts even when compilation fails.
- Restore the direct translation tool as a clean secondary workflow.
- Keep the default local validation stack aligned with backend `9001` and frontend `5173`.

## Non-Goals

- No true autonomous multi-agent planner in this change.
- No requirement to land the future company PDF-translation provider now.
- No requirement to reintroduce likes, favorites, or moderation into the primary community shell.

## Current Baseline

The current implementation already qualifies as a real first-generation paper agent in these ways:

- provider-backed reasoning via configurable LLM API
- internal community paper search
- arXiv-backed external paper search fallback
- silent import / reuse of papers
- bridge into the existing translation workflow

However, it is still missing the conversation shell, user-scoped history, and reading recovery rules needed to feel complete.

## Conversation Workspace

### Route model

- `/` remains the launch surface
- first submit routes to `/agent/:conversationId`
- the conversation page owns transcript rendering, saved chat history, citations, and follow-up prompts

### Persistence model

- conversations are stored under the current authenticated user identity
- if server persistence is unavailable, the first implementation may use user-scoped local persistence
- `New chat` creates a fresh saved conversation instead of merely clearing temporary state

### Answer model

The answer surface should prioritize:

1. concise conclusion
2. paper overview
3. core points / contributions
4. citations
5. next action or current status

Tool traces remain visible, but secondary.

### Homepage launch surface

The homepage itself should stay visually quiet:

- remove summary blocks that foreground tracked / official feed bookkeeping
- keep a single strong agent input as the main first action
- let the first meaningful submit open the dedicated conversation workspace
- keep any supporting paper feed secondary to the launch surface rather than visually above it

## Provider-backed Reasoning Prompt

The first-generation community agent is still backed by a real chat-completions provider, but the prompt must force a paper-native structure instead of a generic assistant reply.

It should behave like a vertical research copilot rather than a general-purpose assistant.

### Prompt goals

- explain papers in Chinese by default unless the user requests another language
- ground every claim in paper context or retrieved citations
- state clearly when the system imported a paper or started translation
- produce answers that are scannable in a conversation page
- preserve multi-turn paper context so follow-up questions remain anchored to the same research thread
- stay within paper-domain tasks such as search, explanation, comparison, reading guidance, and translation handoff

### Response structure

The provider prompt should steer the model toward these sections when relevant:

1. short conclusion / current status
2. paper overview
3. core points or contributions
4. what the user can do next
5. cited papers

This structure is especially important for the homepage launch flow, because the first answer should feel like an alphaXiv-style paper guide, not a generic chat bubble.

## Agent Tool Boundary

The community agent should treat the current direct translation workflow as a callable tool:

- the agent may call the default `en -> zh` translation workflow
- the timeline may show it as a translation tool action
- the standalone translation tool remains available under `Tools`

## Reader Recovery Rules

### English source reader

Preferred order:

1. sanitized local HTML derived from arXiv HTML
2. source PDF
3. abstract + source link fallback

### Translated reader

Preferred order:

1. `preview_html`
2. `translated_pdf`

### Failure recovery

Compile failure does not automatically mean “no translated reading”.

In product terms, compile failure is treated as a packaging / rendering failure of the downstream artifact chain, not as proof that translated HTML content is unreadable.

If a failed task still has translated section outputs or translated PDF artifacts:

- generate / recover `preview_html` when possible
- recover `translated_pdf` when present
- surface the paper as degraded-but-readable instead of fully unavailable

This keeps the current system compatible with the later company PDF-translation fallback. When that provider is integrated, it should also land on the same `translated_pdf` reader contract instead of introducing a separate reader mode.

## Layout Direction

The UI should take clear inspiration from alphaXiv without cloning its branding:

- homepage: a minimal launch surface with one strong input and light supporting context
- conversation page: wide main answer canvas, left saved-history rail, citations and actions integrated into the main conversation flow
- reader page: reader-first shell where reading occupies most of the width and the agent panel is secondary but resizable
- main app sidebar: a compact but labeled text rail that remains coordinated with the canvas width; it should reserve space cleanly instead of behaving like a detached icon strip
- community cards and toolbars: lighter metadata, clearer open-reader affordance, and less emphasis on community-status decoration
- shared shell spacing: the reserved desktop sidebar gap must include the real visible sidebar card offset so the top bar and homepage content never render underneath the sidebar surface

### Reader composition

- move all metadata and system state above the reader
- remove unnecessary bottom clutter
- prefer an article-like HTML presentation closer to arXiv HTML readability
- keep the agent panel available at the same hierarchy level as the reader, with width persistence
- strip upstream arXiv chrome such as navigation, footers, author utility blocks, and side tool panels before rendering local English HTML
- expose an explicit reader-language switch so users can intentionally move between English-source and Chinese-translated reading when both exist
- if English HTML is unavailable, fall back to source PDF before presenting an empty or misleading HTML state

## Validation Strategy

Before final browser QA, the change should have explicit TDD coverage for:

- homepage launch flow
- conversation persistence and replay
- provider-backed answer shaping
- reader recovery and layout states
- source HTML sanitization so local English reading does not leak upstream arXiv shell chrome

Local browser QA must run against the same explicitly started backend instance as the frontend API target, so stale local ports do not mask current paper detail fixes.
The default verification target for this change is the shared local stack:

- backend on `127.0.0.1:9001`
- frontend on `127.0.0.1:5173`
- frontend API base `http://127.0.0.1:9001`

## Tools Restoration

The tools hub must restore the old direct translation workflow as a first-class standalone utility. Community-specific submit framing that leaked into the dashboard should be removed or demoted there, because the community surface is now the main discovery/import entry.

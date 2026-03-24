# Why
- The current community agent is already provider-backed for reasoning, internal search, silent import, and translation bridge, but the UX still behaves like a homepage demo panel instead of an alphaXiv-style conversation workspace.
- The current reader incorrectly treats compile-related task failure as if translated reading is entirely unavailable, even though translated HTML can often still be recovered from translated section outputs.
- The legacy direct translation tool was partially reshaped by community-facing entry logic and now needs to be restored as a clean standalone workflow while remaining callable from the agent.

## What Changes
- Turn the homepage into a launch surface that opens a dedicated conversation workspace after the first submit.
- Remove the old community summary clutter from the homepage launch surface so tracked / official-style overview cards no longer compete with the agent entry.
- Add user-scoped saved conversation history so authenticated users get a Gemini / GPT / alphaXiv-style left-side chat history.
- Upgrade the agent answer surface to emphasize paper overview, core points, citations, and next actions before raw tool traces.
- Tighten the provider-backed agent prompt so the real LLM returns paper-native answers that feel like a research copilot instead of a generic chat reply.
- Make the agent a real paper-domain chat workspace with multi-turn memory, paper-aware follow-ups, and tool use that stays scoped to research tasks.
- Recover translated HTML preview and translated PDF fallback from failed translation tasks whenever usable artifacts still exist.
- Prefer sanitized local English HTML reading, then source PDF, instead of relying on a raw external iframe as the primary reading mode.
- Make the detail page expose an explicit English / Chinese reader-mode switch while still auto-preferring the best available readable mode.
- Refine the homepage, conversation shell, and reader layout with an alphaXiv-inspired composition: minimal launch surface, strong reading focus, and softer secondary chrome.
- Replace the icon-only community rail with a coordinated text sidebar that stays spatially aligned with the main canvas instead of visually colliding with it.
- Fix the shared shell so the reserved sidebar gap, visible sidebar card, sticky top bar, and homepage canvas use coordinated spacing without overlap.
- Simplify community result cards and feed controls so discovery emphasizes paper entry, open-reader action, and translation availability instead of status-heavy chips.
- Restore the legacy direct translation dashboard inside `Tools`, while exposing the same workflow as an agent-callable translation tool.
- Strip more raw arXiv chrome from imported English HTML so local source reading feels like a clean article surface instead of an embedded upstream page shell.
- Add end-to-end validation coverage for the main community flow before final browser QA.
- Run local verification against the default dev stack of backend `9001` + frontend `5173` so browser QA matches `backend/start.bat` and the shared dev scripts.

## Impact
- Affected specs: `community-agent-assistant`, `community-paper-discovery-ui`, `community-public-read-experience`, `community-paper-intake-api`, `web-ui`
- Affected code: community agent backend orchestration, paper detail contract/recovery logic, homepage and conversation workspace routes, reader shell, shared sidebar, paper cards/feed toolbar, legacy tools hub, i18n copy, and local dev runtime scripts

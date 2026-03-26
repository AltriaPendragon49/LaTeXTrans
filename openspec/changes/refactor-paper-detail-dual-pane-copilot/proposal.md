# Change: Refactor paper detail into a dual-pane copilot workspace

## Why
- The current paper detail shell already reserves space for an agent workspace, but it is still closer to a generic detail page plus side panel than to an immersive reading-first copilot experience.
- The agent answer and the reader surface are still too loosely connected for serious paper study; users cannot yet move directly from an assistant citation to the corresponding paper location.
- We need a dedicated dual-pane reading workspace so the paper reader and AI copilot behave like one coordinated study surface.

## What Changes
- Refactor the paper detail page into a persistent dual-pane layout with a reading-dominant main pane and a paper-scoped AI copilot pane.
- Define anchorable citation and action metadata so assistant references can scroll and highlight the corresponding reader location.
- Define soft reader-mode upgrades so a paper can switch from source-first reading to translated HTML without disorienting page replacement.
- Keep the paper detail route and same-paper conversation continuity intact while improving spatial coordination and interaction quality.

## Impact
- Affected specs:
  - `community-paper-discovery-ui`
  - `web-api`
  - `web-ui`
- Affected frontend:
  - paper detail route and reader shell
  - community copilot panel rendering
  - shared paper/detail state management
- Affected backend:
  - paper detail response metadata for stable reader anchors
  - community agent citation/action payloads for anchor targeting
- Follow-up changes required later:
  - deep research mode inside the copilot pane
  - richer section-aware note taking and annotations

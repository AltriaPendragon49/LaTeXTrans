## Context
The paper detail route already has a reading-dominant split workspace, but the header still behaves like a large metadata banner. The approved direction is to compress the header into a minimal control strip so the PDF reader remains visually primary.

## Goals
- Maximize vertical reader space by removing persistent metadata chrome.
- Keep reader mode switching immediately accessible.
- Keep core actions discoverable with small independent icons.
- Preserve access to paper metadata through an on-demand info card instead of an always-open block.

## Non-Goals
- No backend favorite implementation in this change.
- No redesign of the right-side insights and similar-paper panes.
- No change to the translated PDF download backend contract.

## Decisions
- Use a single sticky row for the toolbar with three zones: far-left back button, centered mode switch, right-aligned icon actions.
- Keep the mode switch visually rectangular and lightweight, removing the outer rounded capsule treatment.
- Use an info popover for title, authors, categories, publication time, arXiv id, and repository link when available.
- Keep share scoped to the current detail route URL so users can share the exact page they are reading.

## Risks / Trade-offs
- Removing visible title and metadata from the header can make orientation weaker for first-time readers.
  - Mitigation: keep the info action lightweight and always available in the toolbar.
- Smaller action targets can become harder to use.
  - Mitigation: keep icon buttons visually minimal but maintain accessible click targets and aria labels.

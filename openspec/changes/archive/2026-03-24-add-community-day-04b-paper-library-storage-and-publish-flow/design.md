# Day 04B Design: Community Paper Library Storage And Publish Flow

## Context
Day 4 introduced a paper-owned preview and download surface, but those assets still point back to task-owned local outputs. That creates two problems:

1. a normal `/translate` task does not naturally become a community paper
2. the public community library is coupled to ephemeral task directories and server-specific absolute paths

Day 04B introduces a community-owned library layer without replacing the translation engine.

## Goals / Non-Goals
- Goals:
  - make community papers own copied library assets under a relative data directory
  - let successful authenticated translation tasks become community papers automatically
  - preserve official-first behavior while avoiding duplicate fallback rows for the same arXiv paper
  - keep preview/download APIs working with relative storage references
- Non-Goals:
  - build a full moderation/publish console
  - replace the existing task workspace, history, or `/processing` route
  - build object-storage support in this change

## Decisions
- Decision: Store community assets under `data/community_papers/<paper_id>/...`
  - Why: keeps community assets stable, server-portable, and clearly separated from task working directories
  - Alternatives considered:
    - continue pointing `paper_assets` at task output paths: rejected because it preserves the current coupling
    - rewrite the whole translation engine to be paper-first: rejected because it is too large for Day 04B

- Decision: Persist relative library paths in `paper_assets`
  - Why: avoids machine-specific absolute path leakage and makes deployments portable
  - Alternatives considered:
    - persist absolute paths and normalize later: rejected because it keeps the portability defect in storage

- Decision: Auto-publish completed authenticated tasks after `/translate/{task_id}`
  - Why: fixes the current product gap where user translations do not show up in community unless they started from the community paper detail page
  - Alternatives considered:
    - require a separate manual publish click: rejected because it would still leave Week 1 broken by default

- Decision: Keep official-first conflict handling
  - Why: Day 2 intake rules already define official community papers as stronger than user fallback entries
  - Rule:
    - reuse an existing official paper for the same arXiv id if it does not yet have a completed community result
    - otherwise avoid replacing an already-completed official selection with a fallback task

## Risks / Trade-offs
- Risk: copying source and output files increases disk usage
  - Mitigation: copy only the public community assets needed for browse/preview/download, not the entire task output tree
- Risk: upload-title deduplication is weaker than arXiv-id deduplication
  - Mitigation: Day 04B treats arXiv identity as canonical and uses conservative title fallback for non-arXiv tasks
- Risk: async publish watch only covers tasks started after this change
  - Mitigation: Day 5 can include catch-up notes for older tasks in its demo known-issues record

## Migration Plan
1. Add a new community library storage config directory.
2. Introduce helpers that copy assets into the community library and store relative paths.
3. Refactor community paper asset sync to use the library helpers.
4. Add a publish watcher from the normal translation start path.
5. Validate preview/download against relative stored paths.
6. Update the execution index and Day 5 dependency notes.

## Open Questions
- Whether Day 5 should also add an explicit `/submit` community intake page on top of the new auto-publish behavior.

## Context
- Server evidence from April 18, 2026 shows `2006.11239` and `2305.18290` now produce multiple `payload_invariant_passthrough` sections that remain byte-for-byte English source.
- Local legacy baseline for `2006.11239` only used one target-language compile-first fallback section instead of three full-English section passthroughs.
- Current section flow already attempts paragraph rescue after a payload-invariant failure, but the rescue path can still return `None` and immediately preserve the full source section.
- `2010.11929` source explicitly contains `\usepackage[pdftex]{graphicx}` while the translated zh path prefers XeLaTeX/LuaLaTeX, producing engine-specific primitive/driver failures.

## Goals
- Preserve the existing hard-freeze safety boundary.
- Restore the product rule that translated target-language degradation is preferred over full source-English fallback whenever structurally safe enough to keep.
- Fix the confirmed pdfTeX-driver template incompatibility without weakening general engine selection rules.

## Non-Goals
- Removing hard-freeze verification.
- Reworking the whole LangGraph orchestration shape.
- Broad compile-template heuristics beyond the confirmed pdfTeX-driver incompatibility family.

## Decisions
- Decision: Treat section-level payload-invariant failures as rescue-first states, not immediate source passthrough states.
  - Rationale: the regression is not that hard-freeze rejects invalid output; the regression is that the section-level recovery path gives up too early and surfaces raw English.
- Decision: Keep source preservation only as the final fallback when rescue still cannot produce a materially target-language result.
  - Rationale: this matches `openspec/project.md` and the user’s explicit quality requirement.
- Decision: Normalize explicit pdfTeX package driver declarations before modern CJK compilation.
  - Rationale: `2010.11929` is a concrete failure caused by template engine assumptions, not by translation semantics.

## Risks / Trade-offs
- More aggressive downgrade persistence can keep imperfect Chinese in places that previously stayed English.
  - Mitigation: keep structural validation and only prefer target-language output when it passes the existing shell/placeholder safety checks.
- Template sanitization can affect healthy papers if made too broad.
  - Mitigation: limit the change to explicit driver-locked package forms and cover with focused regression tests.

## Validation Plan
- Add regression tests for section rescue so payload-invariant failures do not revert whole sections to source when paragraph/fragment rescue produced acceptable target-language output.
- Add compile sanitization tests for explicit `pdftex` graphics driver declarations under zh/CJK compilation.
- Re-run focused paper tests for `2006.11239`, `2305.18290`, and `2010.11929`.

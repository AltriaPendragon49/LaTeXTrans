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
  - Rationale: this matches `openspec/project.md` and the user's explicit quality requirement.
- Decision: When a translated section keeps the expected leading section hierarchy, any extra sectioning commands hallucinated into the prose body must be demoted back to plain target-language text before persistence.
  - Rationale: `2305.18290` exposed a narrower post-rescue regression where stray `\section{...}` commands survived inside body text, hurting preview readability even when compile-time recovery remained possible.
- Decision: When a section-level invariant rescue succeeds but leaves degraded heading text, the leading section titles should be rescued independently before the section is persisted.
  - Rationale: `2305.18290` still showed badly degraded Chinese subsection titles after the unsafe passthrough bug was fixed; the body was acceptable, but the heading quality remained much worse than the product rule allows.
- Decision: Normalize explicit pdfTeX package driver declarations before modern CJK compilation.
  - Rationale: `2010.11929` is a concrete failure caused by template engine assumptions, not by translation semantics.

## Risks / Trade-offs
- More aggressive downgrade persistence can keep imperfect Chinese in places that previously stayed English.
  - Mitigation: keep structural validation and only prefer target-language output when it passes the existing shell/placeholder safety checks.
- Section-body sanitization could overcorrect papers whose source body intentionally contains nested sectioning commands.
  - Mitigation: only apply the demotion rule when the source chunk has a leading sectioning block and the remaining source body contains no sectioning commands.
- Template sanitization can affect healthy papers if made too broad.
  - Mitigation: limit the change to explicit driver-locked package forms and cover with focused regression tests.

## Validation Plan
- Add regression tests for section rescue so payload-invariant failures do not revert whole sections to source when paragraph/fragment rescue produced acceptable target-language output.
- Add a regression test for translated section bodies that hallucinate extra `\section` / `\subsection` commands even though the source body has none.
- Add regression coverage for section-level invariant recovery where headings need a separate title-only rescue pass.
- Add compile sanitization tests for explicit `pdftex` graphics driver declarations under zh/CJK compilation.
- Re-run focused paper tests for `2006.11239`, `2305.18290`, and `2010.11929`.

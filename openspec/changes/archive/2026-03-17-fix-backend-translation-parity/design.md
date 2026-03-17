## Overview

This change restores backend translation parity by hardening two places where the current pipeline still deviates from the prototype in user-visible ways:

1. LLM payload preparation can leak display-math delimiters into fail-fast invariant checks, which forces `payload_invariant_passthrough` and leaves large English source spans in the final output.
2. Section-level target-language fallback can over-escape inline LaTeX constructs, producing unreadable text such as `\textasciitilde{}`, `\textbackslash{}`, and escaped math delimiters around formulas and references.

The design keeps the backend's newer safety guarantees, but narrows them so that structure protection no longer destroys readability or translation coverage on math-heavy papers.

## Goals

- Preserve the backend's fail-fast invariant model without letting display math cause false positive passthrough.
- Keep section fallback compilable while preserving safe inline LaTeX constructs that are essential for readability.
- Avoid new external API fields or workflow changes.
- Minimize regression risk by making localized changes in payload preparation and fallback rendering only.

## Non-Goals

- Replacing the current fallback architecture.
- Changing external HTTP APIs or task artifact schemas.
- Rewriting parser chunking or structure-guard logic beyond what is already covered by this change.
- Guaranteeing identical text to the prototype in every paper; the goal is parity on failure behavior and readability, not byte-for-byte output matching.

## Design Decisions

### 1. Protect all math spans before payload invariants

The previous payload-preparation path only isolated inline math. That was sufficient for single-line `$...$` and `\(...\)`, but not for display math written as `$$...$$` or `\[...\]`.

This design introduces a broader math-isolation step before environment masking and residual-structure masking:

- isolate display math first
- isolate inline math second
- preserve placeholder round-tripping through the existing restore path

This keeps the invariant contract intact:

- raw `\begin{...}` / `\end{...}` must still be forbidden in LLM payloads
- raw unmatched `$` must still be forbidden in LLM payloads
- valid math blocks must not be mistaken for invariant violations

The change is intentionally implemented as an extension of the existing payload-preparation pipeline instead of a special-case bypass, so translator and parser agents continue to share the same protection model.

### 2. Preserve safe inline LaTeX constructs during section fallback

`ultimate_downgrade_section_segment()` is intended to produce "ugly but readable" target-language output. In practice, fallback sections became much worse than that when math or reference-like syntax was adjacent to prose.

The design expands the set of tokens that the section fallback renderer treats as safe-to-preserve:

- inline math: `$...$`, `\(...\)`
- display math: `$$...$$`, `\[...\]`
- citation and reference commands such as `\cite...`, `\ref`, `\eqref`, `\autoref`, `\cref`
- footnotes
- common text-formatting commands
- simple links

These constructs are preserved verbatim while neighboring natural language is still downgraded deterministically.

This is safer than trying to "unescape" already-degraded fallback output after the fact because:

- the preserved tokens remain structurally valid LaTeX atoms
- reconstruction still owns document shells and higher-level structure
- we avoid broad textual rewrites that could mutate arbitrary content

### 3. Keep document-boundary protection strict

The design explicitly does not relax document-boundary or shell ownership rules. The earlier fixes that prevent leaked `\begin{document}` / `\end{document}` tokens from surviving in section bodies remain in force.

The new fallback preservation rules therefore apply only to safe inline constructs, not document-level boundaries.

## Data Flow

### Payload preparation

1. Raw section text enters translator or parser payload preparation.
2. All math spans are isolated into placeholders.
3. Environment blocks are isolated.
4. Sensitive commands and residual structure tokens are masked.
5. Fail-fast invariants run on the protected payload.
6. After LLM response handling, masks, environment blocks, and math spans are restored in reverse order.

### Section fallback rendering

1. A fallback section body is sanitized to remove shell-owned document boundary tokens.
2. The body is split by the safe-preserve pattern.
3. Safe inline LaTeX fragments are kept verbatim.
4. Remaining prose fragments are deterministically downgraded and escaped.
5. Preserved section wrappers and shells are reattached.

## Alternatives Considered

### A. Allow raw display math through invariant checks

Rejected because it weakens the invariant model and creates a new exception path that is harder to reason about and audit.

### B. Post-process degraded fallback text with broad literal replacements

Rejected because it is too error-prone. Global replacements of `\textasciitilde{}` or `\textbackslash{}` can mutate legitimate output and mask deeper issues.

### C. Skip fallback entirely for math-heavy sections

Rejected because that would increase English retention and move the backend away from the project's target-language-first policy.

## Risks and Mitigations

### Risk: Preservation pattern becomes too permissive

If the fallback preserve pattern is too broad, unsafe commands might survive fallback and reintroduce structure corruption.

Mitigation:

- preserve only bounded, well-known inline constructs
- keep document-boundary stripping and shell sanitization ahead of fallback rendering
- cover the new preserve set with targeted unit tests

### Risk: Math placeholder ordering diverges during restore

Mitigation:

- reuse the existing placeholder restoration path
- add regression coverage for round-trip restoration of display math

### Risk: Parser and translator payload preparation drift apart

Mitigation:

- use the same math-isolation helper in both agents
- validate both paths through OpenSpec requirements and unit tests

## Validation Strategy

- Unit tests for payload preparation must prove that display math is masked before fail-fast checks and restored byte-for-byte afterward.
- Unit tests for section fallback must prove that formulas, citations, references, and footnotes survive fallback without degrading into escaped literals.
- Existing reconstruction, generator, orchestrator, and deterministic repair tests must stay green to confirm no regression in the surrounding workflow.
- Real-sample replay checks on the three known problem papers must confirm:
  - math-heavy invariant-passthrough sections no longer fail payload preparation
  - rerendered fallback sections no longer emit `\textasciicircum{}`, `\textasciitilde{}`, `\textbackslash{}`, or escaped-dollar artifacts

## Implementation Mapping

- `backend/app/services/latex/utils.py`
  - add broader math-isolation helper covering display and inline math
- `backend/app/services/agents/translator_agent.py`
  - switch payload preparation to the broader math-isolation helper
- `backend/app/services/agents/parser_agent.py`
  - align parser payload protection with translator payload protection
- `backend/app/services/translation/ultimate_downgrade.py`
  - expand the section-fallback preserve pattern to include safe inline LaTeX constructs
- `backend/tests/unit/test_translator_payload_guard.py`
  - add display-math masking and restore regression coverage
- `backend/tests/unit/test_ultimate_downgrade.py`
  - add readable fallback regression coverage around formulas and references

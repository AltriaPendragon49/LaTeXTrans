# Proposal: Restore Structural Integrity

## 1. The Problem
The current LaTeX translation system suffers from a high compilation failure rate. 
- The absence of a "hard freeze" mechanism exposes LaTeX structural elements (math, environments, references) to the LLM, leading to undesired modifications.
- The segmentation strategy based on length/punctuation often breaks macros and environments.
- Output-layer regex repairs (like `_escape_bare_underscores_in_text_mode`) errantly corrupt valid math syntax.
- A "Structural Fallback" forcefully stitches rejected text using regex, causing unrecoverable compilation breakdowns instead of failing cleanly.
- Intrusive compilation defaults (modifying `cls` files, injecting shims) obscure root causes and break user templates.

## 2. The Solution
We propose returning to the structural safety semantics of the prototype while maintaining the current system's concurrency and engineering scale. This revolves around:
1. **Hard Freeze Mechanism:** Mathematically and structurally replacing equations, complex environments, and citations with irreducible placeholders *before* LLM processing.
2. **Structure-Aware Chunking:** Segregating text strictly by AST boundaries (depth=0, outside math/envs) rather than token length.
3. **Fail-Fast Semantics:** Immediately aborting translation when structural placeholders mismatch, explicitly removing the dangerous regex stitching fallback.
4. **Tiered Compilation:** Defaulting to a non-intrusive `latexmk` run, with source modifications only as a last resort.
5. **Environmental Fallback (Image Sanitizer):** Automatically repairing corrupted PDF inclusions via Ghostscript during compilation failures to prevent third-party file errors from breaking the pipeline.

## 3. Scope
- **In Scope:** 
  - Refactoring `parser.py` / `parser_agent.py` for placeholder injection and structure-aware chunking.
  - Refactoring `validator_agent.py` to limit `_escape_bare_underscores_in_text_mode` and enforce strict placeholder consistency.
  - Refactoring `translator_agent.py` to remove `structural_fallback`.
  - Refactoring `compiler.py` to implement a tiered execution strategy and an Image Sanitizer for PDF corruption.
- **Out of Scope:** 
  - Modifying the web frontend.
  - Changing the LangGraph orchestration framework itself (only adjusting its nodes/edges to fail-fast).
  - Adding new LaTeX engines (staying within pdflatex/xelatex/lualatex).

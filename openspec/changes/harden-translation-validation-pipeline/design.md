## Context
14 concurrent translation failures reveal systemic weaknesses in the validation and compilation pipeline. The root cause is the LLM's inability to preserve LaTeX math-mode boundaries during translation. The current `ValidatorAgent` checks command counts, placeholder preservation, and bracket balance, but has no awareness of math-mode delimiter consistency.

## Goals / Non-Goals
- **Goals:**
  - Achieve >90% reduction in "Missing $ inserted" compilation failures.
  - Preserve display math environments natively during math delimiter repair.
  - Make PROTECTED_CMD placeholder restoration robust against LLM mutations.
  - Intelligent, sequence-aware spelling repair of `\input` placeholder tags.
  - Eliminate LLM hallucination in XML/verbatim environments.
  - Resolve ctex package conflicts automatically.
  - Optimize engine selection for xypdf documents.
  - Fix preamble corruption caused by incomplete `\newenvironment` parsing.
  - Detect severe inline translation corruptions (e.g. English leakage, struct damage).
  - Exhaustively repair all math tokens in a single validation pass.

- **Non-Goals:**
  - Full AST-based LaTeX validation (too complex for this iteration).
  - LLM prompt engineering changes (orthogonal concern).
  - Replacing the LLM with a different model.

## Decisions

### Decision 1: Math-Mode Repair in ValidatorAgent (Not Translator)
**What:** Math-mode delimiter validation and repair is placed in `ValidatorAgent._validate_math_delimiters()` rather than in `TranslatorAgent` or `reconstruct.py`.

**Why:** The validator already has access to both `content` (original) and `trans_content` (translated) for each part. It performs structural comparison today (commands, placeholders, brackets). Adding math-delimiter comparison is a natural extension. When mismatches are detected, the repair algorithm can copy delimiter patterns from the original — this is deterministic, not requiring LLM re-translation.

**Alternatives considered:**
- *LLM re-translation with stricter prompt*: Too slow and unreliable — the LLM already failed once.
- *Post-translation regex in TranslatorAgent*: Would duplicate validation logic.
- *Reconstruction-time repair*: Too late — the individual part context is lost by then.

### Decision 2: Occurrence-Based Delimiter Copy from Original
**What:** When `$` count in translation < original, walk both texts in parallel and copy `$` positions from original to translation.

**Algorithm:**
1. Extract all math regions environments securely using regex capturing `$$...$$`, `$...$`, `\[...\]`, `\(...\)`, and `\begin{math/equation/...}...\end{math/equation/...}` from both texts.
2. For each bare math token (`_`, `^`, `\frac`, etc.) in the translation that lacks the protection of an overarching math region, find the corresponding token in the original.
3. If the original token is enclosed in `$...$`, wrap the translation token using the original's pattern.
4. Classify as Type C error (structural fix, no LLM retry).

**Why:** This is deterministic and fast. The original text is the ground truth for where math delimiters belong, and filtering out structural display environments prevents injecting `$` where it's contextually illegal.

### Decision 3: Fuzzy Placeholder Restoration
**What:** `unmask_sensitive_commands` uses a broad regex that tolerates LLM mutations like `\protect\`, extra whitespace, or backslash escaping around `PROTECTED_CMD_N`.

**Pattern:** Instead of exact `<PROTECTED_CMD_N>`, match:
```regex
(?:\\\\protect\\s*\\\\|\\\\)?(?:<|\\{)?PROTECTED_CMD_(\d+)(?:>|\\})?
```

**Fallback:** After regex unmask, scan for any remaining `PROTECTED_CMD` substring; if found, attempt positional-order restoration from mapping.

### Decision 4: Pre-Injection Conflict Scan for ctex
**What:** Before `\usepackage{ctex}`, scan for `\newcommand`, `\renewcommand`, `\def`, `\let`, `\DeclareRobustCommand` that define any command known to conflict with ctex.

**Known conflicts:** `\I`, `\O` (ctex/CJK redefines these).

**Resolution:** Inject `\let\<cmd>\relax` before ctex loading; after ctex, inject `\let\<cmd>\originaldefinition` or re-import the user's definition.

### Decision 5: Intelligent Placeholder Recovery
**What:** Rewrite the `_fix_missing_placeholders` fallback algorithm inside `TranslatorAgent` to stop blindly appending unmapped tags to the EOF.

**Algorithm:**
1. Instead of strict regex, employ `r'<PLACEHOLDER_[^>]+>'` to extract all path-based customized tags (e.g., `\input` file markers).
2. If total extracted counts align but names mismatch, utilize a sequential `.replace()` mapped against the original list index to rectify typographical errors from the LLM.
3. For independently missing tags, calculate standard `_begin`/`_end` relational properties and strictly insert prior to the trailing edge, neutralizing stack corruptions inside `reconstruct.py`.

**Why:** Avoids destructive EOF appending which routinely results in rendering sequence mismatches for path-nested LaTeX `\input` files.

### Decision 6: Exact Preamble Validation
**What:** Modify `get_newcommand_pattern()` to cleanly distinguish `\newcommand` (one argument block) vs `\newenvironment` (two argument blocks).
**Why:** The `\newenvironment` syntax comprises `{name}{begin-code}{end-code}`. By using a monolithic regex, the `end-code` block was regularly dropped from the placeholder footprint, leaving fragments in the main text that derailed the LaTeX compiler entirely.

### Decision 7: Math Repair Exhaustiveness and Corruption Catching
**What:** Upgrade `ValidatorAgent._validate_math_delimiters()` and `repair_math_delimiters()`.
1. Allow `repair_math_delimiters()` to iteratively repair ALL eligible math token omissions concurrently by removing the execution `break`.
2. Evaluate math context strings for untreated English phrases (via standard a-zA-Z frequency analysis or explicit regex) mixed within mathematical closures, marking as Type C despite raw delimiter parity.

**Why:** Earlier limits correctly prioritized safety, but at the cost of abandoning perfectly salvageable documents (e.g., stopping at 1 fix when 51 exist). Furthermore, strict `$ count` equality checks enabled extremely destructive LLM translations to sail past validation if an equal number of broken tags happened to emerge.

### Decision 8: Allow Translation of Container Environments with Nested Placeholders
**What:** Remove the restriction in `parser.py` that marks an environment as `need_trans=False` if it contains `PLACEHOLDER_CAP`. This specifically applies to `frontmatter`, `abstract`, `title`, `author`, and `keywords`.
**Why:** These high-level containers often wrap important text alongside captions. The `TranslatorAgent` is capable of handling nested placeholders, so skipping these blocks results in significant translation gaps.

### Decision 9: CJK-Aware Defensive Fallback and Log Preservation
**What:** 
1. Disable `pdflatex` fallback for documents where `target_language` is `zh/ja/ko`.
2. Archive `.log` files with engine-specific suffixes (e.g., `{jobname}.{engine}.log`) before trying the next engine.
**Why:** For CJK papers, `pdflatex` produces unreadable "garbled" logs that hide the true failures (like BibTeX missing files). Preserving the `lualatex` log is critical for post-mortem analysis.

### Decision 10: Ultra-Flexible Placeholder Repair
**What:** Update `restore_mangled_placeholders` to use a non-greedy wildcard `.*?` or a more symbol-inclusive character class for separators between `PLACEHOLDER`, `TYPE`, and `ID`.
**Why:** Catching `<PLACEHOLDER$_ENV_7>` requires the regex to acknowledge that the LLM may inject math symbols everywhere.

## Risks / Trade-offs
- **Math delimiter copy heuristic** may occasionally wrap non-math content in `$...$` → mitigation: only wrap when original also has `$` at same structural position.
- **Fuzzy unmask** may match false positives → mitigation: only applied to `PROTECTED_CMD` prefix (unlikely to appear in natural LaTeX).
- **ctex conflict list** may be incomplete → mitigation: make it configurable and log warnings for any `\newcommand` collision detected.

## Open Questions
- None (all decisions are straightforward).

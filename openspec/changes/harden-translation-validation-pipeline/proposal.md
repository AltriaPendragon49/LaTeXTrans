# Change: Harden Translation Validation Pipeline

## Why
Analysis of 14 recent failed tasks reveals that **>85% of compilation failures** originate from LLM translation corrupting LaTeX syntax structures. The most prevalent failure modes are:
1. **Missing `$` delimiters** (9/14 tasks): LLM strips math-mode separators, placing `_`, `^`, `\frac` etc. in text mode.
2. **PROTECTED_CMD placeholder restoration failure** (multiple tasks): LLM mutates placeholder format (e.g. adds `\protect\`), causing `unmask_sensitive_commands` regex to miss them.
3. **LLM hallucination in structural environments** (1/14 tasks): LLM generates "refusal" meta-dialogue inside `CCSXML` environment.
4. **`ctex` package command conflict** (1/14 tasks): Injected `ctex` package redefines `\I`, conflicting with author-defined macro.
5. **Suboptimal engine fallback for `xypdf`** (3/14 tasks): System wastes time retrying incompatible engines.
6. **Display Math environments corrupted by `$` bounding** (regression testing): Math delimiter repair algorithm misses `\[...\]` and `\begin{equation}` environments, wrongly inserting `$` inside them.
11. **Placeholder tag misspellings breaking `reconstruct.py`** (regression testing): `TranslatorAgent` fallback reconstruction appends missing `<PLACEHOLDER_...>` tags without preserving their order/pairing, leading to Mismatched tags error.
12. **Preamble parsing bugs** (Task 2602.18680): The `\newenvironment` parsing regex incorrectly matches only one argument, dropping the end-code and corrupting the preamble.
13. **Validator blind spots** (Task 2602.18654): The validator fails to detect severe translation corruption mixed with English text if the total count of math delimiters happens to match.
14. **Insufficient math delimiter repair** (Task 2601.00025): `repair_math_delimiters()` only fixes a single bare token per file, abandoning documents with numerous errors.
15. **Abstract translation skipped due to nested placeholders** (Task 1901.06081): `parser.py` blocks translation of environments (like `frontmatter`) if they contain caption placeholders, causing the entire abstract and title block to remain in the source language.
16. **Internal placeholder mangling** (Task 1901.06081): LLM inserts symbols like `$` inside the placeholder tag (e.g., `<PLACEHOLDER$_ENV_7>`), causing `restore_mangled_placeholders` to fail because it only expects mangling at standard separator boundaries.
17. **Destructive engine fallback for CJK** (Task 1901.06081): The compiler falls back to `pdflatex` when `lualatex` fails on CJK documents, which produces corrupted logs/PDFs that hide the original bibliography/citation errors.

The current `ValidatorAgent` only checks command counts, placeholder sets, and bracket balance — it does **not** verify math-mode delimiter consistency, which is the #1 cause of compilation failure. Likewise, the existing `TranslatorAgent` placeholder matching is brittle against `\input` custom paths and minor spelling typos from the LLM.

## What Changes

### 1. Math-Mode Delimiter Consistency Validation & Auto-Repair (ValidatorAgent)
- Add `_validate_math_delimiters()` to `ValidatorAgent` that compares `$...$` and `$$...$$` counts between original and translation.
- Extract math regions securely by identifying all LaTeX math environments: `$$...$$`, `$...$`, `\[...\]`, `\(...\)`, and `\begin{math/equation/...}...\end{math/equation/...}`.
- When a mismatch is detected, classify as Type C error (structural) and auto-repair by copying math delimiter patterns from original text occurrence-by-occurrence.
- Specifically detect bare math tokens (`_`, `^`, `\frac`, `\sum`, `\int`, `\alpha`, etc.) in text mode and wrap them in `$...$` from original context, strictly avoiding insertion inside existing display math environments.

### 2. Expand Non-Translatable Environment Registry (Parser/Utils)
- Add `CCSXML`, `filecontents`, `filecontents*`, `comment`, `lstlisting`, `verbatim`, `minted` to parser's skip-environment list.
- These environments SHALL be preserved verbatim and never sent to LLM.
- **REFINED**: Modify `_extract_envs` in `parser.py` to allow translation of `frontmatter`, `abstract`, and `title` containers even if they contain caption placeholders, as `TranslatorAgent` is now robust enough to protect nested tags.

### 3. Hardened PROTECTED_CMD Placeholder Mechanism (Utils)
- Make `unmask_sensitive_commands` tolerant of LLM mutations: handle `\protect\PROTECTED_CMD_N`, `\\PROTECTED_CMD_N`, whitespace variations.
- Add post-unmask residual scan: if any `PROTECTED_CMD` text remains in output, force-restore from mapping by fuzzy position matching.
- Add validator check for residual protected command placeholders.
- **REFINED**: Update `restore_mangled_placeholders` in `utils.py` to handle non-alphanumeric characters (specifically `$`, `\`, `_`) appearing *inside* the placeholder name segments or between them.

### 4. CTeX Package Command Conflict Resolution (Reconstruct)
- Before injecting `\usepackage{ctex}`, scan preamble for `\newcommand{\I}`, `\renewcommand{\I}`, `\def\I`, and similar patterns.
- If conflict detected, inject `\let\I\relax` (or the conflicting command) before the ctex import.
- Generalize to a configurable list of known ctex-conflicting commands.

### 5. Engine Selection Optimization & Log Preservation (Compiler)
- Detect `xypdf` package usage and skip `lualatex` engine entirely for those documents.
- **Solution 15**: Update `parser.py` to allow translation of `frontmatter`, `abstract`, `title`, `author`, and `keywords` even if they contain nested `PLACEHOLDER_CAP` tags.
- **Solution 16**: Strengthen `restore_mangled_placeholders` regex in `utils.py` to handle `PLACEHOLDER$_ENV` format.
- **Solution 17**: Upgrade `compiler.py` to preserve independent engine logs (e.g. `BinaryPR_lualatex.log`). For CJK documents, ensure `pdflatex` is only called as the final fallback and its results are excluded from the best-output selection if XeLaTeX or LuaLaTeX successfully produced a PDF.

### 6. Robust Placeholder Tag Restoration (TranslatorAgent)
- Enhance `_fix_missing_placeholders` to capture all structurally generated placeholders including `\input` tags representing files via dynamic paths (regex: `r'<PLACEHOLDER_[^>]+>'`).
- Implement intelligent spelling correction utilizing sequential layout matching for equally-sized tag outputs.
- Build context-aware `_begin` / `_end` pairing repair ensuring matching insertions rather than blind EOF appending.

### 7. Precise Preamble Definition Parsing (Utils)
- Update `get_newcommand_pattern()` to correctly support `\newenvironment` by matching two mandatory `{...}` argument blocks (begin-code and end-code).
- Ensure `\newcommand` and `\newenvironment` are handled with their respective parameter signatures to prevent dropped code blocks during placeholder extraction.

### 8. Strict Translation Corruption Detection (ValidatorAgent)
- Enhance `_validate_math_delimiters()` to not just count `$`, but also verify that the translation does not contain severe untranslated English fragments embedded in math contexts or malformed brace structures.
- Add structural validation for `$...$` blocks to catch prematurely closed or unbalanced delimiters that bypass simple counting.

### 9. Comprehensive Math Delimiter Repair (ValidatorAgent)
- Remove the single-occurrence limit (`break`) in `repair_math_delimiters()` so it can iteratively repair all correctable bare math tokens across the entire document.

## Impact
- Affected specs:
  - `latex-translation-core` (validation, compilation, reconstruction)
- Affected code:
  - `backend/app/services/agents/validator_agent.py` — new `_validate_math_delimiters()` method
  - `backend/app/services/latex/utils.py` — hardened unmask logic, expanded PROTECTED_COMMANDS registry
  - `backend/app/services/latex/reconstruct.py` — ctex conflict resolution
  - `backend/app/services/latex/compiler.py` — xypdf engine skip logic
  - `backend/app/services/agents/parser_agent.py` — expanded skip-environment list
- Behavioral outcome:
  - 9/14 analyzed failures would be prevented by math-delimiter validation alone.
  - PROTECTED_CMD restoration becomes resilient to LLM placeholder mutation.
  - Structural environments are never sent to LLM, eliminating hallucination.
  - ctex command conflicts are resolved automatically before compilation.
  - Compilation engine selection is optimized for xypdf-dependent documents.
  - Display math environments accurately parsed and shielded from naive `$` injections.
  - Typographical mistakes on `<PLACEHOLDER_*>` resolved via sequence without sequence mismatch `reconstruct.py` exceptions.
  - `\newenvironment` defines preserved flawlessly with robust regex handling.
  - Severe structural translation corruptions proactively caught by enhanced validation rules.
  - Hundreds of bare math token errors repaired in a single pass instead of just one.

## 1. Math-Mode Delimiter Validation & Auto-Repair
- [x] 1.1 Add `_validate_math_delimiters(self, part)` to `ValidatorAgent` that counts `$`/`$$` in original vs translation
- [x] 1.2 Implement `repair_math_delimiters(original, translated)` that copies delimiter patterns from original to translation occurrence-by-occurrence
- [x] 1.3 Detect bare math tokens (`_`, `^`, `\\frac`, `\\sum`, `\\int`, etc.) outside `$...$` in translation and wrap using original context
- [x] 1.4 Classify math-delimiter errors as Type C (structural) in `classify_error()`
- [x] 1.5 Integrate `_validate_protected_cmd_residual()` into `_validate()` for type C detection
- [x] 1.6 Remove single-repair limit (`break`) in `repair_math_delimiters` to fix all bare tokens in the file

## 2. Expand Non-Translatable Environment Registry
- [x] 2.1 Add `VERBATIM_ENVS` frozenset with `CCSXML`, `filecontents`, `filecontents*`, `comment`, `lstlisting`, `verbatim`, `minted`, `tikzpicture`, `algorithm` etc.
- [x] 2.2 Force `need_trans=False` in `execute()` for all environments in `VERBATIM_ENVS`

## 3. Harden PROTECTED_CMD Placeholder Mechanism
- [x] 3.1 Add `_PLACEHOLDER_FUZZY_RE` regex in `utils.py` to tolerate `\\protect\\`, `\\`, whitespace, and brace variants around `PROTECTED_CMD_N`
- [x] 3.2 Three-stage restore: exact match → fuzzy match → residual scan (positional order)
- [x] 3.3 Add `_validate_protected_cmd_residual()` to `ValidatorAgent` to flag unreplaced placeholders (→ Type C)
- [x] 3.4 Log warning when fuzzy matching is used for traceability

## 4. CTeX Package Command Conflict Resolution
- [x] 4.1 Add `_detect_ctex_conflicts(preamble)` to `utils.py` that scans for `\\newcommand{\\I}`, `\\def\\I`, etc.
- [x] 4.2 Inject `\\let\\<conflicting_cmd>\\relax` before `\\usepackage{ctex}` when conflicts are detected

## 5. Engine Selection Optimization
- [x] 5.1 Add `xypdf` detection in `compiler.py` that scans for `\usepackage{xypdf}` in tex file
- [x] 5.2 Skip `lualatex` engine for xypdf-dependent documents
- [x] 5.3 Log engine skip reason

## 6. Display Math Environments Protection
- [x] 6.1 Upgrade `_extract_dollar_regions` to `_extract_math_regions` capturing `$$`, `$`, `\[`, `\(`, and `\begin{equation/math/...}`
- [x] 6.2 Ensure `repair_math_delimiters` algorithm ignores bare tokens that fall within these display math regions.
- [x] 6.3 Implement `TestRepairMathDelimiters_DisplayMathEnvironments` unit tests

## 7. Intelligent Placeholder Tag Recovery
- [x] 7.1 Rewrite `TranslatorAgent._fix_missing_placeholders` using regex `r'<PLACEHOLDER_[^>]+>'`
- [x] 7.2 Implement positional sequential replacement for misspellings when tag sums align
- [x] 7.3 Implement pair-oriented `_begin` / `_end` adjacent inserting to avoid `reconstruct.py` stack order exceptions
- [x] 7.4 Implement `test_fix_missing_placeholders.py` unit tests

## 8. Precise Preamble Parsing
- [x] 8.1 Update `get_newcommand_pattern()` regex to distinguish `\newcommand` (one `{body}` arg) and `\newenvironment` (two `{begin}{end}` args)
- [x] 8.2 Add unit tests for `\newenvironment` extraction to guarantee exact preservation

## 9. Strict Translation Corruption Detection
- [x] 9.1 Enhance `_validate_math_delimiters()` to detect severe translation corruption (e.g. English leakage, malformed brackets missing pairing)
- [x] 9.2 Add `TestValidatorAgent_CorruptionDetection` unit tests

## New Fixes

### 1. Math-Mode Delimiter Validation & Auto-Repair
- [ ] **NEW**: Modify `_extract_envs` in `parser.py` to allow `frontmatter`, `abstract`, `title`, `author`, and `keywords` translation despite caption placeholders.

### 2. Placeholder Mechanism Hardening
- [ ] Extend `unmask_sensitive_commands` with fuzzy regex for mutated format.
- [ ] **NEW**: Update `utils.py:restore_mangled_placeholders` to handle internal symbol injections (e.g., `PLACEHOLDER$_ENV`).

### 3. Compiler & CJK Reliability
- [ ] Update `compile_with_intelligent_fallback` to preserve engine-specific logs (e.g. `BinaryPR_lualatex.log`).
- [ ] Implement CJK lockdown: Disable `pdflatex` fallback for CJK-detected documents.

### 4. Preamble & Environment Parsing Fixes
- [ ] Update `get_newcommand_pattern()` to support two-block `\newenvironment`.

### 5. Placeholder Tag Sequence Repair
- [ ] Rewrite `_fix_missing_placeholders` using sequence-based layout matching.

### 6. Validation Logic Upgrades
- [ ] Remove single-fix limit in `repair_math_delimiters()`.
- [ ] Add structural brace and English-leakage detection to `ValidatorAgent`.

### 7. Verification & Regression Testing
- [ ] Run full test suite on problematic papers (2602.18680, 1901.06081).
- [ ] Verify abstract is translated and placeholder leakage is zero.

## 10. Validation
- [ ] 10.1 Re-run failed paper 2602.18440 (Missing $) — verify compilation succeeds after math-mode repair
- [ ] 10.2 Re-run failed paper 2404.10981 (PROTECTED_CMD / CCSXML) — verify compilation succeeds
- [ ] 10.3 Re-run failed paper 2601.00026 (ctex \I conflict) — verify compilation succeeds
- [ ] 10.4 Re-run failed paper 2411.08553 (Mismatched tags) — verify placeholder pair sequencing succeeds
- [x] 10.5 Re-run failed paper 2602.18680 (\newenvironment parsing bug) — verify compilation succeeds
- [x] 10.6 Re-run failed paper 2602.18654 (Severe corruption check) — verify validator flags the error correctly (validation triggers retry)
- [x] 10.7 Re-run failed paper 2601.00025 (Mass math repair) — verify compilation succeeds with all math tokens fixed
- [x] 10.8 Re-run a previously successful paper — verify no regression

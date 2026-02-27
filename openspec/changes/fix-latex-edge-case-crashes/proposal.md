# Proposal: Fix LaTeX Edge Case Crashes

## Motivation
1. The compilation pipeline occasionally encounters documents with CJKutf8 packages present alongside our xeCJK logic, resulting in undefined `CJK` environment errors during XeLaTeX compilation.
2. For engine fallbacks, early LuaLaTeX pages contain strings like `=1` or `0<</S/D>>` due to left-over `\pdfoutput=1` primitives and cross-engine `.aux`/`.out` file contamination (from previously-failed XeLaTeX runs).

## Proposed Change
1. Inject a dummy `CJK` environment dynamically to safely digest unstripped `\begin{CJK}` segments without crashing the XeLaTeX compiler.
2. Globally strip `\pdfoutput=1` during preprocessing.
3. Clean all engine-specific auxiliary compilation state files (like `.aux`, `.out`, `.toc`, etc., but exclude `.bbl`) between automated engine-fallback attempts.

## Impact
- **Translation Resilience:** A vast reduction in the number of "dummy page" or "undefined environment" issues on older or CJK-heavy papers translated to Chinese or Japanese.
- **System Stability:** Ensures LLM hallucinations around environmental blocks will not crash the standard rendering engine.

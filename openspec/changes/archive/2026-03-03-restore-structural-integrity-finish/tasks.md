# Tasks

1.  [x] **Implement Hard Freeze Parser Upgrades**
    *   Modify `backend/app/services/latex/parser.py` to identify math blocks, complex environments, and citations.
    *   Create a placeholder substitution registry `Dict[str, str]`.
    *   Update `backend/app/services/agents/parser_agent.py` to offload identified blocks before generating LLM translation payloads.
    *   *Validation:* Add unit test parsing `main.tex` with figures and inline math to ensure 100% placeholder accuracy.

2.  [x] **Implement Structure-Aware Chunking**
    *   Rewrite `_chunk_long_sections` in `backend/app/services/latex/parser.py`.
    *   Ensure split decisions respect brace depth and environment boundaries instead of strictly relying on `tiktoken` byte counts.
    *   *Validation:* Feed a 4000-token section with nested `itemize` and `textbf` and confirm no macro or environment is split.

3.  [x] **Refactor Translation Agent (Fail-Fast & Pre-Compile)**
    *   Remove `structural_fallback` from `backend/app/services/agents/translator_agent.py`.
    *   Gate `_escape_bare_underscores_in_text_mode` in `backend/app/services/agents/validator_agent.py` to only trigger sequentially on strings outside placeholders.
    *   Implement strict placeholder quantity and type matching in `validator_agent.py`.
    *   *Validation:* Send a translated payload with a modified `[PH_MATH_001]` tag and assert translation fails immediately.

4.  [x] **Refactor Compiler (Tiered Compilation)**
    *   Rewrite `compile_with_intelligent_fallback` in `backend/app/services/latex/compiler.py` into a 3-stage loop: Pristine, Shimmed, and Invasive.
    *   Make `_revert_inputs` in `reconstruct.py` robust against LLM tag hallucinations, replacing `ValueError` with warnings to allow Compile-First Fallback to function.
    *   *Validation:* Provide a mock project with a `IEEEtran.cls` file and ensure Stage 0 does NOT delete the `.cls` file.

5.  [x] **Integration Testing**
    *   Run end-to-end pipeline against a historically failing arXiv directory.
    *   Ensure compilation rate exceeds the benchmark set by the current system.

6.  [x] **Implement Environmental Fallback (Image Sanitizer)**
    *   Add PDF syntax error detection inside the `compiler.py` failure loop (looking for `pdf inclusion: reading image failed`).
    *   Implement a safe Ghostscript distillation function that writes to `*.sanitized.pdf`.
    *   Modify the `.tex` file in-memory or on-disk exclusively to point to the `*.sanitized.pdf` when corruption is detected.
    *   *Validation:* 14 unit tests in `test_sanitizer.py` all pass. Covers extraction, syntax detection, GS distillation, tex patching, and end-to-end flow with mocked subprocesses.

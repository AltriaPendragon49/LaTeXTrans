## Context
Current status: superseded in part by the May 9, 2026 translation-kernel cleanup. This archive remains useful for the parity-kernel decision, but not for the old "keep modern enhancements dormant" assumption. Current production design is stricter: `origin_cli_parity` plus the bounded parity health branch is the only production translation kernel, and unused modern enhancement code has been removed.

The required product behavior is not "better backend translation"; it is exact old-CLI translation-kernel behavior from `texts/origin`. The backend may still handle web concerns such as task creation, storage, status updates, and progress reporting, but the translation kernel itself must behave like the old CLI.

The current backend already has partial legacy flags, especially `enable_legacy_translation_core`, but those flags do not guarantee old-CLI identity. Parser behavior, prompt initialization, LLM request sequencing, validator retry semantics, generator/compiler behavior, route defaults, and orchestration branches can still differ.

The current delivery version is a full backend translation-kernel rollback to old CLI parity. The production path is a single-kernel path: no side-by-side old/new execution, no dual output publication, and no runtime winner selection. Production backend code must be self-contained: legacy behavior is migrated into backend-owned modules, while `texts/origin` is allowed only as the canonical baseline for tests and offline comparison.

## Goals
- The current backend delivery uses backend-owned code that reproduces `texts/origin` old CLI behavior as the translation-kernel behavior.
- Every backend translation trigger uses the same origin parity translation core.
- LangGraph preserves the legacy linear workflow and does not add translation behavior.
- The generated maps, reconstructed `.tex`, compile attempts, and final task outcome are byte-for-byte identical to the old CLI for the same source, config, and mocked LLM responses, except for explicitly wrapper-owned metadata such as task IDs, timestamps, absolute paths, storage URLs, and progress events.
- Newer backend-only enhancement systems are not part of the current production translation kernel when they are unused by parity tasks.

## Non-Goals
- Do not treat removed hard-freeze, repair, diagnostics, structure guard, or fallback code as current production dependencies.
- Do not improve translation quality beyond the old CLI.
- Do not make UI or product workflow changes except where needed to route all task triggers through the same backend kernel.
- Do not run old and new kernels in parallel in production, output two translated results, or choose between old/new kernel outputs at runtime.
- Do not claim stochastic live LLM text will be byte-identical across independent real API calls. Exact parity is defined by identical kernel code behavior, prompts, payloads, ordering constraints, and deterministic mocked-LLM artifacts.

## Recommended Approach
Use a Backend-Owned Origin Parity Kernel.

The parity kernel should migrate the legacy implementation details needed from `texts/origin` into backend-owned modules, with the smallest compatibility layer needed for FastAPI, async task management, and artifact storage. The legacy CLI remains the canonical baseline, and tests compare the backend-owned implementation against it. LangGraph then wraps this backend-owned kernel with a simple graph, rather than allowing modern nodes to participate in translation behavior. Production code must not dynamically import, extend `sys.path` to, or read runtime code from `texts/origin`.

### Alternatives Considered
- Direct dynamic import of `texts/origin`: fastest route to initial parity, but rejected for production because backend containers mount only `backend/`, making repo-root legacy paths brittle and violating the backend-owned runtime boundary.
- Keep current backend and add more flags: lower churn, but it has already proven insufficient because old-CLI identity depends on many hidden parser, validator, generator, and orchestration details.
- Rewrite the old CLI behavior from memory: too risky because "same effect" requires preserving incidental behavior, not only high-level stages.

## Architecture
1. Config normalization
   - Introduce a single internal parity setting such as `translation_core_mode = "origin_cli_parity"`.
   - All translation triggers set or inherit this mode.
   - User-provided advanced settings cannot re-enable modern kernel systems for parity tasks.

2. LangGraph wrapper
   - Compile a parity graph containing only:
     - `parse`
     - `translate`
     - `validate_retry`
     - `generate`
     - `finalize`
   - `validate_retry` must reproduce the legacy coordinator retry loop: initial validation, set translation mode to retry when errors exist, then at most three retry rounds.
   - The parity graph must not include repair, ultimate downgrade, post-compile fallback, precompile structure abort, residual-English fallback, or diagnostic nodes.

3. Origin parity agents
   - Parser writes byte-for-byte identical `inputs_map.json`, `envs_map.json`, `captions_map.json`, `newcommands_map.json`, and `sections_map.json` kernel artifacts as `texts/origin` for deterministic inputs.
   - Translator initializes backend-owned prompt snapshots copied from the legacy CLI, uses the same prompt text, request payload fields, timeout behavior, per-request settings, section concurrency, retry behavior, and fallback-to-source behavior as `texts/origin`.
   - Validator returns and persists errors using the old validator semantics and drives only the old retranslation loop.
   - Generator reconstructs and compiles with the same old semantics, including pdflatex first and xelatex retry for the default legacy path.

4. Trigger routing
   - Normal upload and direct arXiv requests use parity by default.
   - Batch requests create independent parity tasks.
   - Admin/community curation keeps its production limits and metadata flow, but its translation task uses parity.
   - Community paper bridge, content pool prewarm, and community-agent `start_translation_kernel` call the same parity task entry.

5. Unused modern systems
   - Existing modern modules were originally expected to remain present, but this was superseded by the May 9 cleanup when unused production-kernel enhancement code was removed.
   - Parity task config and task logs must make clear that backend-only enhancement systems are not part of production parity execution: hard-freeze orchestration, structure guard, controlled repair, ultimate downgrade, post-compile target-language fallback, compile diagnostics, residual-English fallback, intelligent compiler fallback, RAG or terminology mutation, and any backend-only quality improvement path.

6. Single-kernel production runtime
   - Production execution runs exactly one translation kernel per task: `origin_cli_parity`.
   - The backend must not shadow-run a modern kernel, persist dual kernel outputs, expose dual result choices, or choose a result by comparing old and new kernel outputs.
   - Parity comparison tooling is allowed only in tests, scripts, or explicit offline diagnostics, not in production task execution.
   - Production backend code must not import or load `texts/origin`, `src.formats`, or `src.agents`; all legacy-kernel behavior needed at runtime must live under `backend/`.

7. Precedence over existing modern specs
   - For `origin_cli_parity` tasks, the old CLI parity contract takes precedence over archived specs that require hard-freeze, structure guard, diagnostics, deterministic repair, downgrade, target-language fallback, RAG or terminology mutation, intelligent compilation fallback, or other backend-only translation behavior.
   - Those archived systems can apply again only if a future approved spec reintroduces them with production code.

## Verification Strategy
- Add mocked LLM parity tests that run the legacy CLI path and backend LangGraph parity path against the same small LaTeX fixtures.
- Assert identical LLM payload sequence where concurrency is deterministic or compare by stable request identity when legacy concurrency can complete in different orders.
- Assert byte-for-byte kernel artifact identity for `sections_map.json`, `envs_map.json`, `captions_map.json`, `newcommands_map.json`, `inputs_map.json`, reconstructed `.tex`, selected compile engine sequence, and task result status, excluding only wrapper-owned metadata listed above.
- Add no-invocation tests or runtime assertions proving modern systems are not called during parity tasks.
- Add runtime-boundary tests proving production backend code has no dynamic dependency on `texts/origin` or legacy `src.*` modules.
- Extend `scripts/compare_backend_cli_parity.py` or add a companion script to fail on map/schema/content differences relevant to the kernel.
- Add route/config tests proving every backend trigger produces parity config.
- Add production-path tests or assertions proving a task creates only one kernel execution and one translated output lineage.

## Risks And Mitigations
- Live LLM calls can vary even with the same prompt. Mitigation: define exact kernel parity through payload and deterministic mocked responses, not through independent stochastic API output.
- Copying old behavior can drift from the legacy baseline. Mitigation: keep deterministic parity tests against `texts/origin`, but ensure production runtime imports only backend-owned modules.
- Modern reliability features are being bypassed or removed. Mitigation: make the task log and current specs explicit so future work can reintroduce them only through a separate approved spec.
- Older specs contained modern-kernel requirements. Mitigation: current specs now define parity as the production source of truth and treat those systems as archived historical context.

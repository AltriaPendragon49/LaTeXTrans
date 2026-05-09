## 1. Design And Inventory
Current status: superseded in part by the May 9, 2026 translation-kernel cleanup. Items that mention retaining modern repair, hard-freeze, diagnostics, structure guard, or fallback nodes should be read as historical transition work. Current production code removes unused modern-kernel enhancement code from the parity path.

- [x] 1.1 Inventory every backend translation trigger and confirm it reaches one shared task entry.
- [x] 1.2 Inventory all current modern-kernel toggles and mark which must be forced off in parity tasks.
- [x] 1.3 Choose the adapter import/sync mechanism for `texts/origin` code and document the boundary in code comments.

## 2. Parity Kernel Implementation
- [x] 2.1 Add internal `origin_cli_parity` config normalization for backend translation tasks.
- [x] 2.2 Implement a LangGraph parity graph with only parse, translate, validate_retry, generate, and finalize.
- [x] 2.3 Make parity parser behavior match `texts/origin` map generation.
- [x] 2.4 Make parity translator behavior match `texts/origin` prompts, request payloads, ordering, retry, and source fallback behavior.
- [x] 2.5 Make parity validator and generator behavior match `texts/origin` retry and compile semantics.
- [x] 2.6 Ensure modern repair, hard-freeze, diagnostics, structure guard, and fallback nodes are not invoked by parity tasks. Current cleanup supersedes the original retention assumption by removing unused production-kernel enhancement code.
- [x] 2.7 Ensure production task execution cannot run a second modern kernel, emit dual results, or select between old/new kernel outputs.
- [x] 2.8 Ensure existing modern-kernel spec behavior is scoped out of `origin_cli_parity` execution unless a future approved spec re-enables it.

## 3. Trigger Integration
- [x] 3.1 Route normal upload and direct arXiv translation through parity config.
- [x] 3.2 Route batch translation items through parity config.
- [x] 3.3 Route admin/community curation translation through parity config.
- [x] 3.4 Route community paper bridge and content-pool prewarm translation through parity config.
- [x] 3.5 Route community-agent `start_translation_kernel` translation through parity config.
- [x] 3.6 Record effective parity mode and not-invoked modern systems in task logs/config snapshots.

## 4. Verification
- [x] 4.1 Add mocked-LLM fixtures that run both `texts/origin` and backend parity paths.
- [x] 4.2 Compare map artifacts, reconstructed `.tex`, compile engine sequence, and workflow status byte-for-byte except for explicit wrapper metadata.
- [x] 4.3 Add route/config tests for every trigger class.
- [x] 4.4 Add a production-path assertion or test that each translation task has exactly one kernel execution lineage.
- [x] 4.5 Add no-invocation tests or assertions for retained modern systems during parity tasks.
- [x] 4.6 Run focused backend parity tests.
- [x] 4.7 Run `openspec validate refactor-backend-origin-cli-parity --strict --no-interactive`.
- [x] 4.8 Add a production runtime guard proving backend code does not import or load repo-root `texts/origin`.

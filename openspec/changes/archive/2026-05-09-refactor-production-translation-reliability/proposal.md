# Change: Refactor production translation reliability

## Current Status
Partially superseded by the May 9, 2026 translation-kernel cleanup. Queue, token-pool, production quality, and community publishing concerns may still be useful historical context. Modern translation-kernel fallback/downgrade/repair paths described here are not current production design unless reintroduced by a future approved spec; current production translation uses `origin_cli_parity` plus the bounded parity health branch.

## Why
Community paper production has published unusable translations: large English passthrough sections, repeated fixed Chinese downgrade phrases, and API-failure fallbacks being treated as successful translation output. The current system optimizes for local throughput in ways that amplify one API key or relay under pressure, especially section-internal parallel calls and a token pool that mostly reacts after failures.

## What Changes
- Replace token-hash queueing and global LLM semaphore behavior with task-level LLM member leasing, per-member request limits, pool-level shared limits, bounded backoff, and explicit single-key versus multi-independent-account modes.
- Disable section-internal environment/caption concurrency by default and restore the old effective section model: concurrent sections only within the task-level LLM budget, with environments and captions processed sequentially inside a section.
- Remove fake Chinese fallback from final outputs; API failures, quota failures, and fixed downgrade phrases become explicit failure or retry states, not translated content.
- Add a real structural fallback path that emits semantically translated plain Chinese paragraphs in minimal LaTeX structure when structured translation fails but the model can still translate text.
- Add a community production quality gate before publishing canonical assets. The gate is strict against fake fallback and large source passthrough, but tolerant of normal English terms, citations, math, references, code, and very small isolated source fallback.

## Impact
- Affected specs: `queue-token-isolation`, `translation-orchestration`, `latex-translation-core`, `community-paper-library-storage`
- Affected code: task queue admission, LLM token pool/client wrappers, translator agent section/env/caption scheduling, fallback/downgrade paths, task logs, community asset sync/publish flow, production backfill tooling
- Migration: existing bad community assets should be detected by the new gate and queued for retranslation/backfill rather than silently remaining as healthy published translations.

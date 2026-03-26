## 1. OpenSpec
- [x] 1.1 Add proposal, tasks, and design for `add-community-agent-content-pool-foundation`
- [x] 1.2 Add delta specs for `community-paper-intake-api`, `community-public-read-experience`, `community-agent-assistant`, and `community-content-pool-foundation`
- [x] 1.3 Validate with `openspec validate add-community-agent-content-pool-foundation --strict --no-interactive`

## 2. Pipeline foundation
- [x] 2.1 Define the background discovery and admission flow for pool candidates
- [x] 2.2 Define canonical paper reuse and deduplication rules
- [x] 2.3 Define prewarm stages for source acquisition, translation, preview generation, and indexing
- [x] 2.4 Define bounded concurrency, retries, and failure containment for the worker pipeline

## 3. Product behavior
- [x] 3.1 Define when the agent prefers prewarmed translated evidence over on-demand translation
- [x] 3.2 Define how the reader benefits from prewarmed readable assets
- [x] 3.3 Keep interactive import and translation fallback behavior available for misses

## 4. Operations
- [x] 4.1 Define operator-visible readiness, freshness, and failure signals
- [x] 4.2 Define source throttling and abuse-safe fetch limits
- [x] 4.3 Define minimum logging and replayability for pool jobs
- [x] 4.4 Require authenticated operator access for content-pool readiness and job-log endpoints

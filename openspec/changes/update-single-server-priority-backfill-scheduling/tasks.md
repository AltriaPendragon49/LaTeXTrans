## 1. Scheduler Foundation
- [ ] 1.1 Introduce a dual-lane single-server scheduler with `interactive` priority and opportunistic `backfill` capacity borrowing.
- [ ] 1.2 Add cooperative yield requests plus durable resume checkpoints at approved orchestration boundaries.
- [ ] 1.3 Keep compile-slot isolation and one-paper LangGraph execution semantics intact while the outer scheduler changes.

## 2. Token Pool And Post-Success Isolation
- [ ] 2.1 Implement a health-aware token pool with cooldown tracking, short request-local retry, fast failover, and explicit all-token-exhausted behavior.
- [ ] 2.2 Reduce wasteful backfill retry churn when the whole token pool is exhausted without penalizing interactive retries.
- [ ] 2.3 Move terminology-table generation and success-only compilation diagnostics behind resumable sidecar feature flags while keeping failure diagnostics synchronous.

## 3. Verification
- [ ] 3.1 Add lane-aware runtime observability needed to verify queue priority, yielding, resume, and token-pool behavior.
- [ ] 3.2 Build a small regression corpus with about two papers per issue type: baseline, math-dense, environment-heavy, fallback-sensitive, and pause/resume-sensitive.
- [ ] 3.3 Add automated coverage for priority scheduling, checkpoint resume, token failover, all-pool exhaustion, compile-slot protection, and feature-flag rollback.
- [ ] 3.4 Validate the OpenSpec change with `openspec validate update-single-server-priority-backfill-scheduling --strict --no-interactive`.

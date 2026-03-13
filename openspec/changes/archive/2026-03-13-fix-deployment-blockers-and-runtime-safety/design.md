## Context
Production deployment is constrained by shared-server policy and runtime-only container strategy:
- Host loopback publishing only (`127.0.0.1:9001:9001`)
- Nginx as sole public ingress
- Runtime image must not include business code
- No Docker-in-Docker

Current implementation had correctness and safety gaps under these constraints.

## Goals
- Keep runtime-only architecture intact.
- Eliminate nested docker behavior in runtime containers.
- Align production worker default with current runtime-state model.
- Remove frontend env/security deployment hazards.
- Ensure docs and spec match executable behavior.

## Non-Goals
- No runtime-state externalization redesign (Redis, distributed queue, etc.).
- No feature additions to translation pipeline behavior.

## Decisions
- Decision: Keep container host binding `0.0.0.0` and enforce host loopback publishing.
  - Rationale: preserves Docker networking while satisfying shared-server restrictions.
- Decision: In container runtime or missing docker, force HostLatexExecutor.
  - Rationale: Host executor means current runtime environment LaTeX binaries; avoids nested docker.
- Decision: Enforce single worker by default.
  - Rationale: runtime state (SSE/progress/intermediate task state) is still partially in-process.
- Decision: Remove all frontend fallback behavior to localhost API.
  - Rationale: silent fallback causes production misrouting and hidden outage modes.
- Decision: Add `CORS_ORIGINS` parser with wildcard rejection.
  - Rationale: explicit allowlist only.

## Risks and Mitigations
- Risk: Existing operators rely on `VITE_API_URL`.
  - Mitigation: hard fail with explicit missing-env error and updated deployment docs.
- Risk: Existing multi-worker runtime launch scripts.
  - Mitigation: Docker runtime command updated to workers=1 and startup warning logged.

## Migration Plan
1. Deploy backend/frontend code with new env contract.
2. Set `VITE_API_BASE_URL` in frontend environments.
3. Set `CORS_ORIGINS` explicitly in backend `.env` for production domains.
4. Rotate leaked service-role key before restart.
5. Restart service via systemd.

## Rollback Plan
- Revert this change commit.
- Restore previous env variable usage only if necessary for emergency rollback.
- Keep key rotation regardless of code rollback.

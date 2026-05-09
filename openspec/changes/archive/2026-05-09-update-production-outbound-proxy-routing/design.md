## Context
The production host currently runs `latextrans-backend` and `latextrans-worker` as host-networked Docker containers behind systemd. The request is to speed up external access, especially arXiv source downloads and related external academic fetches, but without forcing known direct destinations such as `one-api.bltcy.top` and `*.niutrans.com` through the proxy.

## Goals
- Keep a local outbound proxy service enabled by default after reboot.
- Route selected external destinations through the proxy without touching public ingress.
- Keep direct routing for the explicitly exempted destinations.
- Avoid breaking backend startup if the proxy is temporarily unavailable.

## Non-Goals
- No change to Nginx, Cloudflare tunnel, MySQL, Redis, or public bind ports.
- No transparent system-wide TUN takeover for all traffic.
- No application-level refactor of all HTTP clients in this pass.

## Decisions
- Use `mihomo` on the Ubuntu host because the requested subscription is Clash-compatible and `mihomo` has straightforward Linux service support.
- Keep routing at the service boundary instead of patching every HTTP client callsite. The backend and worker will consume a local proxy endpoint through environment variables.
- Use `NO_PROXY` to force direct access for `one-api.bltcy.top`, `.niutrans.com`, loopback/private ranges, and the local service fabric.
- Implement fail-open at service startup with a wrapper: if `mihomo` is healthy, inject proxy env vars; otherwise start the container direct.

## Risks / Trade-offs
- Mid-run proxy failure is not a perfect fail-open path because existing in-process HTTP clients will still point at the local proxy until the service restarts.
  Mitigation: keep `mihomo` under `Restart=always`, expose a health endpoint, and keep the startup wrapper fail-open for any subsequent backend restart.
- Environment-variable proxying is broader than arXiv-only usage, so exempt lists must be carefully set.
  Mitigation: set conservative `NO_PROXY` defaults and add explicit direct routing rules in `mihomo`.
- Subscription-generated YAML can change shape.
  Mitigation: update the file with a Python YAML rewrite instead of brittle text replacement.

## Migration Plan
1. Install `mihomo` binary and a dedicated systemd service.
2. Materialize the subscription config, then inject local ports, controller, DNS/listener settings, and direct rules.
3. Add a small launcher script that conditionally exports proxy env vars.
4. Override backend and worker systemd units to use the launcher.
5. Restart `mihomo`, then restart backend and worker one at a time and verify health plus routing.

## Rollback
- Stop and disable `mihomo`.
- Remove the backend/worker systemd overrides and launcher script.
- Reload systemd and restart backend/worker with their original direct Docker commands.

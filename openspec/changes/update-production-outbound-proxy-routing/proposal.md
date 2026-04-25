# Change: Route selected production outbound traffic through a local proxy

## Why
Production arXiv source fetching and other external academic requests can be slow or unstable from the current server network path. The server needs an always-on outbound proxy path for selected external destinations, while keeping critical product traffic and known domestic endpoints on direct access.

## What Changes
- Install a local `mihomo` service on the production Ubuntu host and enable it on boot.
- Feed `mihomo` from the provided Clash subscription and add explicit direct-routing rules for `one-api.bltcy.top` and `*.niutrans.com`.
- Start `latextrans-backend` and `latextrans-worker` through a proxy-aware wrapper so external HTTP(S) calls use the local proxy when it is healthy.
- Preserve a fail-open startup path so backend services can still start direct if the local proxy is unavailable during restart.

## Impact
- Affected code: production systemd/runtime wiring on the server, plus local operations records in this change
- Affected behavior: outbound routing for backend-initiated external HTTP(S) requests
- Non-goals: changing frontend ingress, local database/networking, or existing public service bind addresses

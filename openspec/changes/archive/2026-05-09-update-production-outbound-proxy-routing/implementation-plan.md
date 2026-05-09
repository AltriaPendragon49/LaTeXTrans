# Production Outbound Proxy Routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable a boot-persistent local `mihomo` proxy on production and route selected backend outbound traffic through it while keeping explicit direct exemptions.

**Architecture:** Install `mihomo` as a host-level systemd service fed by the Clash subscription, then start backend/worker containers through a small wrapper that injects `HTTP_PROXY`/`HTTPS_PROXY` only when `mihomo` is healthy. Enforce direct bypasses with both `NO_PROXY` and `mihomo` direct rules so exempt destinations avoid the proxy path.

**Tech Stack:** Ubuntu 24.04, systemd, Docker, `mihomo`, Python + PyYAML

---

### Task 1: Prepare rollout record and safety boundaries

**Files:**
- Modify: `openspec/changes/update-production-outbound-proxy-routing/tasks.md`
- Reference: `/etc/systemd/system/latextrans-backend.service`
- Reference: `/etc/systemd/system/latextrans-worker.service`

- [ ] **Step 1: Confirm the running service topology before changes**

Run:
```powershell
@'
import paramiko
host='82.156.76.218'; username='ubuntu'; password='NiuTrans2026'
commands=[
  'systemctl cat latextrans-backend.service',
  'systemctl cat latextrans-worker.service',
  'docker ps --format "table {{.Names}}\t{{.Status}}"'
]
client=paramiko.SSHClient(); client.set_missing_host_key_policy(paramiko.AutoAddPolicy()); client.connect(hostname=host, username=username, password=password, timeout=20, banner_timeout=20, auth_timeout=20)
for cmd in commands:
    stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
    print(stdout.read().decode("utf-8", errors="replace"))
    err = stderr.read().decode("utf-8", errors="replace")
    if err:
        print(err)
client.close()
'@ | python -
```
Expected: both backend services are still the current Docker-run units and are healthy before rollout.

- [ ] **Step 2: Keep the scope constrained to host-side runtime wiring**

Constraint checklist:
```text
- Do not change Nginx listeners
- Do not change Cloudflare tunnel service
- Do not change MySQL/Redis bind addresses
- Do not modify backend application code in this rollout
```

### Task 2: Install and configure `mihomo`

**Files:**
- Create: `/etc/mihomo/config.yaml`
- Create: `/etc/systemd/system/mihomo.service`
- Create: `/usr/local/bin/mihomo`

- [ ] **Step 1: Download and install the Linux amd64 `mihomo` binary**

Run on the server:
```bash
set -euo pipefail
TMP_DIR="$(mktemp -d)"
cd "$TMP_DIR"
curl -fsSL https://api.github.com/repos/MetaCubeX/mihomo/releases/latest -o release.json
ASSET_URL="$(python3 - <<'PY'
import json
obj=json.load(open('release.json','r',encoding='utf-8'))
for asset in obj.get('assets', []):
    name = asset.get('name', '')
    if 'linux-amd64' in name and name.endswith('.gz') and 'compatible' not in name:
        print(asset['browser_download_url'])
        break
PY
)"
curl -fsSL "$ASSET_URL" -o mihomo.gz
gunzip -f mihomo.gz
chmod +x mihomo
sudo install -m 0755 mihomo /usr/local/bin/mihomo
/usr/local/bin/mihomo -v
rm -rf "$TMP_DIR"
```
Expected: `mihomo -v` prints a version and exits successfully.

- [ ] **Step 2: Fetch the subscription and rewrite it into a stable local config**

Run on the server:
```bash
sudo mkdir -p /etc/mihomo
curl -fsSL 'https://rwbzp.no-mad-sub.one/link/J0UJj25QGYxR6Usx?clash=3&extend=1' -o /tmp/mihomo-subscription.yaml
python3 - <<'PY'
from pathlib import Path
import yaml

src = Path('/tmp/mihomo-subscription.yaml')
dst = Path('/tmp/mihomo-config.yaml')
cfg = yaml.safe_load(src.read_text(encoding='utf-8'))
if not isinstance(cfg, dict):
    raise SystemExit('subscription did not return a YAML mapping')

cfg['mixed-port'] = 7890
cfg['allow-lan'] = False
cfg['bind-address'] = '127.0.0.1'
cfg['mode'] = cfg.get('mode') or 'rule'
cfg['log-level'] = cfg.get('log-level') or 'info'
cfg['ipv6'] = False
cfg['external-controller'] = '127.0.0.1:7897'
cfg['secret'] = 'latextrans-mihomo-local'
rules = list(cfg.get('rules') or [])
prepend_rules = [
    'DOMAIN,one-api.bltcy.top,DIRECT',
    'DOMAIN-SUFFIX,niutrans.com,DIRECT',
]
cfg['rules'] = prepend_rules + rules
dst.write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False), encoding='utf-8')
PY
sudo install -m 0644 /tmp/mihomo-config.yaml /etc/mihomo/config.yaml
```
Expected: `/etc/mihomo/config.yaml` exists and contains the local listener/controller settings plus the direct rules.

- [ ] **Step 3: Create and enable the `mihomo` systemd service**

Service content:
```ini
[Unit]
Description=Mihomo Proxy Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/local/bin/mihomo -d /etc/mihomo
Restart=always
RestartSec=5
LimitNOFILE=1048576

[Install]
WantedBy=multi-user.target
```

Run:
```bash
sudo tee /etc/systemd/system/mihomo.service >/dev/null <<'EOF'
[Unit]
Description=Mihomo Proxy Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/local/bin/mihomo -d /etc/mihomo
Restart=always
RestartSec=5
LimitNOFILE=1048576

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now mihomo
sudo systemctl status mihomo --no-pager -l | head -n 20
```
Expected: `mihomo` is active and listening on `127.0.0.1:7890` and `127.0.0.1:7897`.

### Task 3: Add fail-open proxy injection for backend and worker

**Files:**
- Create: `/usr/local/bin/latextrans-docker-run-with-proxy.sh`
- Create: `/etc/systemd/system/latextrans-backend.service.d/override.conf`
- Create: `/etc/systemd/system/latextrans-worker.service.d/override.conf`

- [ ] **Step 1: Add the proxy-aware Docker launcher**

Launcher content:
```bash
#!/usr/bin/env bash
set -euo pipefail

container_name="$1"
runtime_role="$2"
port="$3"

proxy_args=()
no_proxy_value='127.0.0.1,localhost,::1,172.21.64.24,172.21.64.1,127.0.0.0/8,10.0.0.0/8,172.16.0.0/12,172.17.0.0/16,172.18.0.0/16,172.19.0.0/16,172.20.0.0/14,192.168.0.0/16,.niutrans.com,niutrans.com,one-api.bltcy.top'

if curl -fsS --max-time 2 http://127.0.0.1:7897/version >/dev/null 2>&1; then
  proxy_args+=(
    -e HTTP_PROXY=http://127.0.0.1:7890
    -e HTTPS_PROXY=http://127.0.0.1:7890
    -e ALL_PROXY=http://127.0.0.1:7890
    -e NO_PROXY="$no_proxy_value"
    -e http_proxy=http://127.0.0.1:7890
    -e https_proxy=http://127.0.0.1:7890
    -e all_proxy=http://127.0.0.1:7890
    -e no_proxy="$no_proxy_value"
  )
fi

exec /usr/bin/docker run \
  --name "$container_name" \
  --network host \
  --env-file /srv/LaTexTrans/backend/.env \
  -e BACKEND_RUNTIME_ROLE="$runtime_role" \
  "${proxy_args[@]}" \
  -v /srv/LaTexTrans/backend:/app/backend \
  latextrans-backend:prod \
  uvicorn backend.app.main:app --host 127.0.0.1 --port "$port" --workers 1 --proxy-headers --forwarded-allow-ips='*' --timeout-keep-alive 120 --log-level info
```

Run:
```bash
sudo tee /usr/local/bin/latextrans-docker-run-with-proxy.sh >/dev/null <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

container_name="$1"
runtime_role="$2"
port="$3"

proxy_args=()
no_proxy_value='127.0.0.1,localhost,::1,172.21.64.24,172.21.64.1,127.0.0.0/8,10.0.0.0/8,172.16.0.0/12,172.17.0.0/16,172.18.0.0/16,172.19.0.0/16,172.20.0.0/14,192.168.0.0/16,.niutrans.com,niutrans.com,one-api.bltcy.top'

if curl -fsS --max-time 2 http://127.0.0.1:7897/version >/dev/null 2>&1; then
  proxy_args+=(
    -e HTTP_PROXY=http://127.0.0.1:7890
    -e HTTPS_PROXY=http://127.0.0.1:7890
    -e ALL_PROXY=http://127.0.0.1:7890
    -e NO_PROXY="$no_proxy_value"
    -e http_proxy=http://127.0.0.1:7890
    -e https_proxy=http://127.0.0.1:7890
    -e all_proxy=http://127.0.0.1:7890
    -e no_proxy="$no_proxy_value"
  )
fi

exec /usr/bin/docker run \
  --name "$container_name" \
  --network host \
  --env-file /srv/LaTexTrans/backend/.env \
  -e BACKEND_RUNTIME_ROLE="$runtime_role" \
  "${proxy_args[@]}" \
  -v /srv/LaTexTrans/backend:/app/backend \
  latextrans-backend:prod \
  uvicorn backend.app.main:app --host 127.0.0.1 --port "$port" --workers 1 --proxy-headers --forwarded-allow-ips='*' --timeout-keep-alive 120 --log-level info
EOF
sudo chmod 0755 /usr/local/bin/latextrans-docker-run-with-proxy.sh
```
Expected: the script exists and is executable.

- [ ] **Step 2: Override backend and worker unit ExecStart**

Run:
```bash
sudo mkdir -p /etc/systemd/system/latextrans-backend.service.d
sudo tee /etc/systemd/system/latextrans-backend.service.d/override.conf >/dev/null <<'EOF'
[Unit]
After=mihomo.service
Wants=mihomo.service

[Service]
ExecStart=
ExecStart=/usr/local/bin/latextrans-docker-run-with-proxy.sh latextrans-backend web 9001
EOF

sudo mkdir -p /etc/systemd/system/latextrans-worker.service.d
sudo tee /etc/systemd/system/latextrans-worker.service.d/override.conf >/dev/null <<'EOF'
[Unit]
After=mihomo.service
Wants=mihomo.service

[Service]
ExecStart=
ExecStart=/usr/local/bin/latextrans-docker-run-with-proxy.sh latextrans-worker worker 9002
EOF

sudo systemctl daemon-reload
sudo systemctl restart latextrans-backend
sudo systemctl restart latextrans-worker
```
Expected: both services restart successfully and continue listening on `127.0.0.1:9001` and `127.0.0.1:9002`.

### Task 4: Verify routing and service health

**Files:**
- Reference: `/etc/mihomo/config.yaml`
- Reference: `journalctl -u mihomo`

- [ ] **Step 1: Verify listeners and backend health**

Run:
```bash
ss -ltnp | egrep '7890|7897|9001|9002'
curl -fsS http://127.0.0.1:9001/api/health
curl -fsS http://127.0.0.1:9002/api/health
curl -fsS http://127.0.0.1:7897/version
```
Expected: all four endpoints respond; health returns JSON and Mihomo returns version info.

- [ ] **Step 2: Verify direct-bypass destinations are not forced through the proxy**

Run:
```bash
docker exec latextrans-worker /bin/sh -lc 'env | grep -i proxy'
docker exec latextrans-worker /bin/sh -lc 'python - <<'"'"'PY'"'"'
import requests
for url in [
    "https://one-api.bltcy.top/v1/models",
    "https://niutrans.com",
]:
    try:
        r = requests.get(url, timeout=15, allow_redirects=True)
        print(url, r.status_code)
    except Exception as e:
        print(url, "ERROR", e)
PY'
```
Expected: requests complete without backend outage; the direct exemptions remain reachable.

- [ ] **Step 3: Verify proxied external fetch path still works**

Run:
```bash
docker exec latextrans-worker /bin/sh -lc 'python - <<'"'"'PY'"'"'
import requests
for url in [
    "https://export.arxiv.org/api/query?id_list=2508.18791",
    "https://export.arxiv.org/e-print/2508.18791",
]:
    try:
        r = requests.get(url, timeout=20, allow_redirects=True)
        print(url, r.status_code, len(r.content))
    except Exception as e:
        print(url, "ERROR", e)
PY'
```
Expected: both requests succeed, confirming the worker can still reach the targeted external path.

- [ ] **Step 4: Mark the OpenSpec task checklist complete**

Update `openspec/changes/update-production-outbound-proxy-routing/tasks.md` so all implemented items are checked after live verification succeeds.

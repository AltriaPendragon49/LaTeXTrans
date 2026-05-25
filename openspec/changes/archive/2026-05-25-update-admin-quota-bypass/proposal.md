# Change: Admin daily LaTeX quota bypass

## Why
Admin users need to run translation tests and community/admin workflows without being blocked by the product's local daily LaTeX quota. Today the default per-user quota of 3 items can stop an admin account before verification or operational work is complete.

## What Changes
- Treat any authenticated user whose resolved roles include `admin` as exempt from the local daily LaTeX translation quota.
- Keep the daily quota unchanged for non-admin authenticated users.
- Keep upstream/provider quotas, queue limits, batch-size limits, active-task limits, and NiuTrans PDF direct-translation credits unchanged.
- Return quota snapshots in a way that does not present admin users as blocked by the local daily quota.

## Impact
- Affected specs: `web-api`, `batch-translation`
- Affected code: backend quota service, translation start routes, batch translation/upload quota checks, auth quota snapshot responses, relevant unit tests
- No database schema change is expected.

# Pandorick read-only integration

The adapter uses only HTTP GET through `ReadOnlyHttpClient`. The base URL must resolve syntactically to `http://127.0.0.1` or `http://localhost`. POST, PUT, PATCH and DELETE raise `ReadOnlyViolationError`. Polling is disabled by default.

Verified live on 2026-07-26 and enabled in the allowlist:

| Endpoint | Envelope data |
|---|---|
| `/api/v1/health` | service heartbeat fields |
| `/api/v1/system/status` | modules, data collectors, database/storage and error summary |
| `/api/v1/brain/status` | sanitized latest decision and brain status |
| `/api/v1/decisions/recent?limit=100` | bounded `decisions` array and limit |
| `/api/v1/statistics` | analyses, developer, simulated-trading and storage aggregates |
| `/api/v1/warnings` | warnings, counts and last error |

Every endpoint returns `status`, `generated_at`, `data_age_seconds`, `source`, `version` and `data`. `/api/v1/learning/summary` and `/api/v1/graph/overview` exist but timed out during verification, so Stimpy does not poll them. No recent-outcomes endpoint was found. No endpoint was added to Pando.

Activation after explicit approval: copy `.env.example` to an untracked `.env`, set only `STIMPY_PANDORICK_ENABLED=true`, start `python -m stimpy`, and check `/api/stimpy/source-status`. Disable by restoring false and restarting. Retry/backoff failures produce isolated source status; they never stop Pandorick.

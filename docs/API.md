# Stimpy read-only API

Loopback default: `http://127.0.0.1:8765`. All endpoints use GET; all write methods return HTTP 405. `limit` is clamped to 1–100 and `offset` is non-negative.

- `/api/stimpy/health`
- `/api/stimpy/status`
- `/api/stimpy/source-status`
- `/api/stimpy/observations/recent`
- `/api/stimpy/memory`
- `/api/stimpy/evidence/recent`
- `/api/stimpy/reasoning/recent`
- `/api/stimpy/critic/recent`
- `/api/stimpy/patterns`
- `/api/stimpy/workflow-results/recent`
- `/api/stimpy/graph`
- `/api/stimpy/statistics`

Payloads come from already sanitized bounded observations or small projections. Tokens, authorization headers, cookies, absolute source paths and raw unbounded Pandorick responses are not stored or emitted.

Evidence, Reasoning and Critic endpoints return persisted internal analysis records with stable IDs. They support bounded `limit` and `offset`, and none represents advice, an order or approval for Pandorick.

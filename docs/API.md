# Stimpy read-only API

The local browser view is served at `/controlcenter` with same-origin CSS and JavaScript. It consumes only the GET endpoints, refreshes every 15 seconds and exposes no write control.

Loopback default: `http://127.0.0.1:8765`. All endpoints use GET; all write methods return HTTP 405. `limit` is clamped to 1–100 and `offset` is non-negative.

- `/api/stimpy/health`
- `/api/stimpy/status`
- `/api/stimpy/source-status`
- `/api/stimpy/observations/recent`
- `/api/stimpy/memory`
- `/api/stimpy/evidence/recent`
- `/api/stimpy/reasoning/recent`
- `/api/stimpy/critic/recent`
- `/api/stimpy/incubation`
- `/api/stimpy/patterns`
- `/api/stimpy/hypotheses`
- `/api/stimpy/hypotheses/{id}`
- `/api/stimpy/hypotheses/{id}/evidence`
- `/api/stimpy/hypotheses/{id}/evaluation`
- `/api/stimpy/hypotheses/{id}/reasoning`
- `/api/stimpy/hypotheses/{id}/critic`
- `/api/stimpy/hypotheses/{id}/lifecycle`
- `/api/stimpy/hypothesis-incubations`
- `/api/stimpy/training-runs`
- `/api/stimpy/training-runs/{run_id}/metrics`
- `/api/stimpy/workflow-results/recent`
- `/api/stimpy/graph`
- `/api/stimpy/statistics`

Payloads come from already sanitized bounded observations or small projections. Tokens, authorization headers, cookies, absolute source paths and raw unbounded Pandorick responses are not stored or emitted.

Evidence, Reasoning and Critic endpoints return persisted internal analysis records with stable IDs. They support bounded `limit` and `offset`, and none represents advice, an order or approval for Pandorick.

`/api/stimpy/incubation` returns bounded task projections and accepts an optional status filter. It remains GET-only; creating, reactivating, cancelling and recording failures are internal explicit service operations, not HTTP endpoints.

`/api/stimpy/patterns` returns persisted Pattern projections with bounded `limit`, `offset` and an optional status filter. It reports `model_updates=0` and `causal_claims=0`. Learning cases cannot be submitted through HTTP.

Hypothesis projections are GET-only:

- `/api/stimpy/hypotheses` supports bounded pagination and an optional status filter.
- `/api/stimpy/hypotheses/{id}` returns one persisted hypothesis.
- `/api/stimpy/hypotheses/{id}/evidence` returns bounded append-only evidence projections.
- `/api/stimpy/hypotheses/{id}/evaluation` returns the latest explicitly persisted evaluation.
- `/api/stimpy/hypotheses/{id}/reasoning` returns the latest immutable hypothesis analysis.
- `/api/stimpy/hypotheses/{id}/critic` returns its latest persisted self-criticism.
- `/api/stimpy/hypotheses/{id}/lifecycle` returns bounded immutable reject/archive audit events.
- `/api/stimpy/hypothesis-incubations` lists bounded incubation projections and accepts an optional status filter.

Creating hypotheses, adding evidence, evaluating, analysing, incubating, reactivating, rejecting and archiving are local Python service operations. There is no HTTP write endpoint.

Training-run projections are GET-only. Metrics accept bounded pagination plus optional `hypothesis_key` and `split` filters. They expose descriptive persisted aggregates, never trading instructions or automatically promoted evidence.

Shitzo S.1 adds no HTTP endpoint. Its foundation remains disconnected and disabled; later projections must be GET-only and must never expose trade controls.

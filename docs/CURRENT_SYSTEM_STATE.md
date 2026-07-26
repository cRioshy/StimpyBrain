# Current system state

Date: 2026-07-26. StimpyBrain Phase 2 is a standalone Python service. Composition occurs in `stimpy/app.py`; importing it starts nothing. `python -m stimpy` starts a local GET-only API and one controlled worker. The Pandorick poller is installed but disabled by default.

## Architecture and services

Verified Pandorick Rick API GET envelopes flow through `ReadOnlyHttpClient -> ObservationAdapter -> ObservationNormalizer -> ObservationStore`. The store appends sanitized raw records to rotating JSONL and maintains a synchronized SQLite index. New records feed evidence-counted Memory, descriptive Learning and the internal observe-only Workflow Gate. The Knowledge Graph and local HTTP API expose bounded projections.

Active only when started: Stimpy worker and local API. Pandorick polling additionally requires `STIMPY_PANDORICK_ENABLED=true`; its default is false. There are no broker, order, Telegram or Pandorick-write components.

## Entry points and data flow

- `python -m stimpy`: controlled start/stop.
- `stimpy/app.py`: dependency composition.
- `stimpy/http_client.py`: local GET-only transport with timeout/retry/backoff.
- `stimpy/normalizer.py`: schema, timestamps, stable IDs/hashes, limits and redaction.
- `stimpy/observation_store.py`: JSONL and SQLite schema v2.
- `stimpy/worker.py`: single in-process instance, atomic state and bounded shutdown.
- `stimpy/api.py`: nine bounded GET endpoints; all write methods return 405.

## Workflow, learning and history

Workflow topology remains exactly `DataQuality -> Features -> Prediction -> MomentumGate -> RiskGate -> DecisionGate`, optionally followed only by disabled `PaperSimulation`. Only terminal states persist. Phase-2 decisions without strict price fields are internally rejected as insufficient data rather than bypassing DataQuality. Results never leave Stimpy.

Memory records store subject/relation/object, source observation IDs, evidence and contradiction counts, bounded confidence, status and `causal=false`. Learning only aggregates patterns; model updates and causal claims remain zero.

## Storage and commands

`stimpy_data/{observations,memory,state,database,logs}` is local and Git-ignored. Observations use rotating append-only JSONL plus SQLite metadata offsets. SQLite foreign keys are enabled and Stimpy schema migration is version 2. Tests: `python -m compileall -q stimpy tests`; `python -m unittest discover -v`.

## Risks

Pandorick `/api/v1/learning/summary` and `/api/v1/graph/overview` timed out during verification and are excluded from polling. No outcome-recent endpoint exists. Authentication is not implemented in Stimpy’s local API, so it must remain loopback-only. The worker singleton is process-local, not a cross-process OS lock. See `KNOWN_PROBLEMS.md`.

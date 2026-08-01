# Current system state

Date: 2026-08-01. StimpyBrain is a standalone Python service. Composition occurs in `stimpy/app.py`; importing it starts nothing. `python -m stimpy` starts a local GET-only API and one controlled worker. The Pandorick poller is installed but disabled by default. A separate local reasoning prototype can process caller-supplied simulated records and is not wired into that worker.

## Architecture and services

Verified Pandorick Rick API GET envelopes flow through `ReadOnlyHttpClient -> ObservationAdapter -> ObservationNormalizer -> ObservationStore`. The store appends sanitized raw records to rotating JSONL and maintains a synchronized SQLite index. New records feed evidence-counted Memory, descriptive Learning and the internal observe-only Workflow Gate. The architecture Knowledge Graph and local HTTP API expose bounded projections.

The isolated prototype flows through `Observer -> Memory facade -> EvidenceEngine -> ReasoningEngine -> SelfCritic -> KnowledgeGraph`. It reuses the same JSONL/SQLite store. Evidence, Reasoning, Critic, Incubation, Pattern and Knowledge records have stable IDs and are stored idempotently in SQLite schema v6. Incubation and Pattern Learning advance only through explicit service calls; no background scheduler or worker connection exists.

Active only when started: Stimpy worker and local API. Pandorick polling additionally requires `STIMPY_PANDORICK_ENABLED=true`; its default is false. There are no broker, order, Telegram or Pandorick-write components.

## Entry points and data flow

- `python -m stimpy`: controlled start/stop.
- `stimpy/app.py`: dependency composition.
- `stimpy/http_client.py`: local GET-only transport with timeout/retry/backoff.
- `stimpy/normalizer.py`: schema, timestamps, stable IDs/hashes, limits and redaction.
- `stimpy/observer.py`: strict normalization of caller-supplied prototype payloads.
- `stimpy/observation_store.py`: rotating JSONL and SQLite schema v6.
- `stimpy/evidence.py`, `reasoning.py`, `self_critic.py`: pure heuristic analysis.
- `stimpy/incubation_service.py`: explicit persistent task creation, readiness, reactivation, comparison, cancellation and bounded failure handling.
- `stimpy/pattern_learning.py`: explicit persisted comparable-case grouping, regime separation, contradiction counting and thresholded Pattern status.
- `stimpy/prototype.py`: isolated prototype orchestration and Incubation protocol boundary.
- `stimpy/demo_reasoning_prototype.py`: temporary, simulated local demo.
- `stimpy/worker.py`: single in-process instance, atomic state and bounded shutdown.
- `stimpy/api.py`: thirteen bounded GET endpoints; all write methods return 405.

## Workflow, learning and history

Workflow topology remains exactly `DataQuality -> Features -> Prediction -> MomentumGate -> RiskGate -> DecisionGate`, optionally followed only by disabled `PaperSimulation`. Only terminal states persist. Phase-2 decisions without strict price fields are internally rejected as insufficient data rather than bypassing DataQuality. Results never leave Stimpy.

Memory records store subject/relation/object, source observation IDs, evidence and contradiction counts, bounded confidence, status and `causal=false`. The older `LearningService` remains a descriptive memory summary. Phase-C `PatternLearningService` separately groups persisted independent cases by market, symbol, decision and market regime; model updates and causal claims remain zero. Prototype Evidence exposes a separate quality score. Reasoning separates caller confidence from bounded reasoning confidence and records assumptions and missing information. Self Critic stores severity and calibration warnings. Reprocessing the same observation or Pattern case is idempotent.

## Storage and commands

`stimpy_data/{observations,memory,state,database,logs}` is local and Git-ignored. Observations use rotating append-only JSONL plus SQLite metadata offsets. Analysis uses `evidence_results`, `reasoning_results`, `critic_results`, `incubation_tasks`, `patterns`, `pattern_cases` and `knowledge_entries`. SQLite foreign keys are enabled and Stimpy schema migration is version 6. Tests: `python -m compileall -q stimpy tests`; `python -m unittest discover -s tests -v`. Demo: `python -m stimpy.demo_reasoning_prototype`.

## Risks

Pandorick `/api/v1/learning/summary` and `/api/v1/graph/overview` timed out during verification and are excluded from polling. No outcome-recent endpoint exists. Authentication is not implemented in Stimpy’s local API, so it must remain loopback-only. The worker singleton is process-local, not a cross-process OS lock. See `KNOWN_PROBLEMS.md`.

Pattern Learning exists, but is explicitly triggered and limited to exact comparable-case groups. Incubation also intentionally has no automatic scheduler. Pattern and Evidence rules are illustrative descriptive thresholds, not calibrated probabilities.

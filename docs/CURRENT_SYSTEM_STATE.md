# Current system state

SQLite schema v15 adds disabled-by-default Social Memory Lite: public RSS and official Reddit API observation, transparent rule classification, restart-safe reaction jobs, historical matches and bounded read-only Controlcenter/API projections. The active composition does not use X/Twitter and is isolated from Shitzo and Pandorick.

Date: 2026-08-15. StimpyBrain is a standalone Python service. Composition occurs in `stimpy/app.py`; importing it starts nothing. `python -m stimpy` starts a local GET-only API, one controlled worker and the Shitzo collector only when explicitly enabled. The Pandorick poller and Shitzo autorun are disabled by default.

## Architecture and services

Verified Pandorick Rick API GET envelopes flow through `ReadOnlyHttpClient -> ObservationAdapter -> ObservationNormalizer -> ObservationStore`. The store appends sanitized raw records to rotating JSONL and maintains a synchronized SQLite index. New records feed evidence-counted Memory, descriptive Learning and the internal observe-only Workflow Gate. The architecture Knowledge Graph and local HTTP API expose bounded projections.

SQLite schema v13 supports Shitzo's validated records, frozen windows, deterministic traders, virtual PaperBroker and GET-only projections. An optional continuous collector uses a public credential-free GET ticker and is activated only by two explicit environment flags.

Active only when started: Stimpy worker and local API. Pandorick polling additionally requires `STIMPY_PANDORICK_ENABLED=true`. Continuous Shitzo collection requires `SHITZO_ENABLED=true` and `SHITZO_AUTORUN=true`; both are false by default. Its virtual broker has no real execution path.

## Entry points and data flow

- `python -m stimpy`: controlled start/stop.
- `stimpy/app.py`: dependency composition.
- `stimpy/http_client.py`: local GET-only transport with timeout/retry/backoff.
- `stimpy/normalizer.py`: schema, timestamps, stable IDs/hashes, limits and redaction.
- `stimpy/observer.py`: strict normalization of caller-supplied prototype payloads.
- `stimpy/observation_store.py`: rotating JSONL and SQLite schema v10.
- `stimpy/offline_replay.py`: explicit chronological OHLCV CSV replay with stable runs and split-safe cases.
- `stimpy/pandorick_training.py`: explicit, filtered decision/outcome ZIP analysis for five descriptive hypothesis families.
- `stimpy/shitzo/`: paper-research foundation, virtual broker, pure traders and tick orchestration.
- `stimpy/public_market_feed.py`, `shitzo_collector.py`: credential-free GET feed and explicitly enabled continuous collection loop.
- `stimpy/social/lite_worker.py`, `stimpy/social/adapters/`: RSS/Reddit observation and restart-safe T0/+5m/+30m/+2h/+24h reaction processing.
- `stimpy/evidence.py`, `reasoning.py`, `self_critic.py`: pure heuristic analysis.
- `stimpy/incubation_service.py`: explicit persistent task creation, readiness, reactivation, comparison, cancellation and bounded failure handling.
- `stimpy/pattern_learning.py`: explicit persisted comparable-case grouping, regime separation, contradiction counting and thresholded Pattern status.
- `stimpy/hypothesis_engine.py`: local creation, append-only evidence linkage, independence deduplication and conservative idempotent evaluation.
- `stimpy/prototype.py`: isolated prototype orchestration and Incubation protocol boundary.
- `stimpy/hypothesis_analysis.py`: immutable Hypothesis Reasoning/Critic and explicit evidence-gated incubation.
- `stimpy/hypothesis_lifecycle.py`: explicit audited reject/archive commands and terminal-state enforcement.
- `stimpy/demo_reasoning_prototype.py`: temporary, simulated local demo.
- `stimpy/worker.py`: single in-process instance, atomic state and bounded shutdown.
- `stimpy/api.py`: bounded GET projections including read-only Shitzo status/accounts/positions/decisions/trades; all write methods return 405.
- `stimpy/static/controlcenter.*`: dependency-free responsive read-only dashboard for live paper activity and Hypothesis research, served locally by the existing API server.

## Workflow, learning and history

Workflow topology remains exactly `DataQuality -> Features -> Prediction -> MomentumGate -> RiskGate -> DecisionGate`, optionally followed only by disabled `PaperSimulation`. Only terminal states persist. Phase-2 decisions without strict price fields are internally rejected as insufficient data rather than bypassing DataQuality. Results never leave Stimpy.

Memory records store subject/relation/object, source observation IDs, evidence and contradiction counts, bounded confidence, status and `causal=false`. The older `LearningService` remains a descriptive memory summary. Phase-C `PatternLearningService` separately groups persisted independent cases by market, symbol, decision and market regime; model updates and causal claims remain zero. Prototype Evidence exposes a separate quality score. Reasoning separates caller confidence from bounded reasoning confidence and records assumptions and missing information. Self Critic stores severity and calibration warnings. Reprocessing the same observation or Pattern case is idempotent.

Phase D.1 stores research questions as Hypotheses, never as facts. D.2 adds immutable Reasoning/Critic records and explicit incubation. D.3 adds reasoned local rejection and archival. D.4 adds a read-only Controlcenter for overview, search/filter, evidence, evaluation, analysis, critic, incubation and lifecycle history. Inspiration and Knowledge Graph promotion remain disconnected.

## Storage and commands

`stimpy_data/{observations,memory,state,database,logs}` is local and Git-ignored. SQLite foreign keys are enabled and the latest Stimpy schema migration is version 15. Tests: `python -m compileall -q stimpy tests`; `python -m unittest discover -s tests -v`.

## Risks

Pandorick `/api/v1/learning/summary` and `/api/v1/graph/overview` timed out during verification and are excluded from polling. No outcome-recent endpoint exists. Authentication is not implemented in Stimpy’s local API, so it must remain loopback-only. The worker singleton is process-local, not a cross-process OS lock. See `KNOWN_PROBLEMS.md`.

Pattern Learning exists, but is explicitly triggered and limited to exact comparable-case groups. Incubation also intentionally has no automatic scheduler. Pattern and Evidence rules are illustrative descriptive thresholds, not calibrated probabilities.

Hypothesis thresholds and confidence are illustrative rather than statistically calibrated. D.4 displays stored values but neither recalculates nor changes them. There is no automatic data collection, scheduler, Inspiration Engine or Knowledge Graph promotion.

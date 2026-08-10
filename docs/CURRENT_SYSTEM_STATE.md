# Current system state

Date: 2026-08-01. StimpyBrain is a standalone Python service. Composition occurs in `stimpy/app.py`; importing it starts nothing. `python -m stimpy` starts a local GET-only API and one controlled worker. The Pandorick poller is installed but disabled by default. A separate local reasoning prototype can process caller-supplied simulated records and is not wired into that worker.

## Architecture and services

Verified Pandorick Rick API GET envelopes flow through `ReadOnlyHttpClient -> ObservationAdapter -> ObservationNormalizer -> ObservationStore`. The store appends sanitized raw records to rotating JSONL and maintains a synchronized SQLite index. New records feed evidence-counted Memory, descriptive Learning and the internal observe-only Workflow Gate. The architecture Knowledge Graph and local HTTP API expose bounded projections.

The isolated prototype flows through `Observer -> Memory facade -> EvidenceEngine -> ReasoningEngine -> SelfCritic -> KnowledgeGraph`. SQLite schema v13 also supports disabled Shitzo S.4: validated records, frozen windows, deterministic traders, virtual PaperBroker, explicit tick-by-tick `ShitzoLab` orchestration and GET-only projections. No provider, scheduler or automatic activation exists.

Active only when started: Stimpy worker and local API. Pandorick polling additionally requires `STIMPY_PANDORICK_ENABLED=true`; its default is false. Shitzo does not start with Stimpy and its virtual broker has no real execution path. There are no real broker, order, Telegram or Pandorick-write components.

## Entry points and data flow

- `python -m stimpy`: controlled start/stop.
- `stimpy/app.py`: dependency composition.
- `stimpy/http_client.py`: local GET-only transport with timeout/retry/backoff.
- `stimpy/normalizer.py`: schema, timestamps, stable IDs/hashes, limits and redaction.
- `stimpy/observer.py`: strict normalization of caller-supplied prototype payloads.
- `stimpy/observation_store.py`: rotating JSONL and SQLite schema v10.
- `stimpy/offline_replay.py`: explicit chronological OHLCV CSV replay with stable runs and split-safe cases.
- `stimpy/pandorick_training.py`: explicit, filtered decision/outcome ZIP analysis for five descriptive hypothesis families.
- `stimpy/shitzo/`: disabled paper-research foundation, virtual broker, pure traders and explicit no-thread/no-network Lab orchestration.
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
- `stimpy/static/controlcenter.*`: dependency-free responsive read-only Hypothesis dashboard, served locally by the existing API server.

## Workflow, learning and history

Workflow topology remains exactly `DataQuality -> Features -> Prediction -> MomentumGate -> RiskGate -> DecisionGate`, optionally followed only by disabled `PaperSimulation`. Only terminal states persist. Phase-2 decisions without strict price fields are internally rejected as insufficient data rather than bypassing DataQuality. Results never leave Stimpy.

Memory records store subject/relation/object, source observation IDs, evidence and contradiction counts, bounded confidence, status and `causal=false`. The older `LearningService` remains a descriptive memory summary. Phase-C `PatternLearningService` separately groups persisted independent cases by market, symbol, decision and market regime; model updates and causal claims remain zero. Prototype Evidence exposes a separate quality score. Reasoning separates caller confidence from bounded reasoning confidence and records assumptions and missing information. Self Critic stores severity and calibration warnings. Reprocessing the same observation or Pattern case is idempotent.

Phase D.1 stores research questions as Hypotheses, never as facts. D.2 adds immutable Reasoning/Critic records and explicit incubation. D.3 adds reasoned local rejection and archival. D.4 adds a read-only Controlcenter for overview, search/filter, evidence, evaluation, analysis, critic, incubation and lifecycle history. Inspiration and Knowledge Graph promotion remain disconnected.

## Storage and commands

`stimpy_data/{observations,memory,state,database,logs}` is local and Git-ignored. SQLite foreign keys are enabled and Stimpy schema migration is version 13. Tests: `python -m compileall -q stimpy tests`; `python -m unittest discover -s tests -v`.

## Risks

Pandorick `/api/v1/learning/summary` and `/api/v1/graph/overview` timed out during verification and are excluded from polling. No outcome-recent endpoint exists. Authentication is not implemented in Stimpy’s local API, so it must remain loopback-only. The worker singleton is process-local, not a cross-process OS lock. See `KNOWN_PROBLEMS.md`.

Pattern Learning exists, but is explicitly triggered and limited to exact comparable-case groups. Incubation also intentionally has no automatic scheduler. Pattern and Evidence rules are illustrative descriptive thresholds, not calibrated probabilities.

Hypothesis thresholds and confidence are illustrative rather than statistically calibrated. D.4 displays stored values but neither recalculates nor changes them. There is no automatic data collection, scheduler, Inspiration Engine or Knowledge Graph promotion.

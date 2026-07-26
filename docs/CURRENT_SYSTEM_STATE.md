# Current system state

## Goal and safety boundary

StimpyBrain is a standalone passive observer, append-only memory, descriptive learner, workflow safety gate, knowledge graph projection, and read-only in-process API. It has no active Pandorick connection, broker adapter, Telegram sender, order function, or configuration for live mode.

## Architecture and data flow

`Pandorick (future read-only event copy) -> ObservationAdapter -> ObservationStore (SQLite) -> MemoryService -> LearningService -> KnowledgeGraph -> ReadOnlyAPI`.

Separately, copied market observations may pass through the exact workflow topology `DataQuality -> Features -> Prediction -> MomentumGate -> RiskGate -> DecisionGate -> optional PaperSimulation`. Mode is always `observe`; the decision is prefixed `OBSERVE_`; order count is always zero; paper simulation is disabled.

## Components and entry points

- `stimpy/observation_adapter.py`: allowlist and boundary validation; invoked explicitly, no subscriber loop.
- `stimpy/observation_store.py`: synchronized append-only SQLite observations.
- `stimpy/workflow_service.py`: default safe workflow facade.
- `stimpy/memory_service.py`: counts, symbol/topic relations, correlation sequences and contradictions.
- `stimpy/learning_service.py`: descriptive snapshot only; no model mutation.
- `stimpy/knowledge_graph.py`: StimpyBrain cluster projection.
- `stimpy/api.py`: read-only in-process queries; no write routes/server.

## Persistence and controls

SQLite uses foreign keys, integrity check, synchronized writes, unique event IDs, terminal-only workflow statuses, atomic workflow audits, sanitizer redaction/hashing/previews, and migration version 1. Workflow event and correlation IDs are idempotent. Observation correlation IDs may repeat intentionally to represent a sequence; event IDs remain unique.

## Commands

No long-running service exists yet. Tests: `python -m compileall -q stimpy tests` and `python -m unittest discover -v` from the project root.

## Risks

No authenticated HTTP API, retention policy, real Pandorick event-schema contract, or production migration tooling exists. The deterministic prediction is a placeholder and must not be interpreted as trading advice.

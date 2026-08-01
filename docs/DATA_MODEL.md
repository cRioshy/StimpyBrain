# Data model

Observation schema v1 contains `observation_id`, `event_id`, `correlation_id`, `source`, `source_endpoint`, `source_type`, UTC observed/source timestamps, symbol, market, sanitized payload, deterministic SHA-256 content hash and schema version. SQLite metadata additionally records JSONL filename, byte offset, payload size, processing status and creation time.

Memory schema v1 contains the required identity/type/timestamps, source observation IDs, subject/relation/object, evidence and contradiction counts, bounded confidence, status, last verification, content and schema version. Allowed statuses are `OBSERVED`, `REPEATED`, `PROVISIONAL`, `SUPPORTED`, `CONTRADICTED`, `ARCHIVED`. Content explicitly records `causal=false`.

Workflow results contain their internal ID, observation foreign key, terminal status, reasons, gates and creation time. SQLite foreign keys are enabled for each store/repository connection.

Foundation schema v4 adds:

- `evidence_results`: stable evidence/observation IDs, raw and normalized scores, independent quality score, supporting and contradicting evidence, count, timestamp and schema version.
- `reasoning_results`: stable reasoning/observation/evidence IDs, evidence score, reasons, counterarguments, assumptions, missing information, cautious conclusion, separate confidence and uncertainty.
- `critic_results`: stable critic/observation/reasoning IDs, issues, `INFO|LOW|MEDIUM|HIGH|CRITICAL` severity, suggestions and calibration warning.
- `knowledge_entries.reasoning_id` and `knowledge_entries.critic_id`: links provisional knowledge to its analysis records.

All three result tables are idempotent per observation. Existing results are retained rather than silently overwritten. `CANCELLED` is a valid observation outcome.

Phase-B schema v5 adds `incubation_tasks`. Each task retains its initial observation/reasoning, status, due time, optional final reasoning, new observation IDs, conclusion, comparison deltas, direction-change flag, failure count and safe error type. Allowed states are `NEW`, `INCUBATING`, `READY`, `RESOLVED`, `FAILED` and `CANCELLED`. First and second analyses remain separate records.

Phase-C schema v6 adds `patterns` and `pattern_cases`. A Pattern has a stable content-derived ID, type, normalized grouping conditions, balanced positive/negative/unresolved counts, evidence and contradiction counts, bounded confidence, status and UTC timestamps. Allowed states are `OBSERVED`, `PROVISIONAL`, `SUPPORTED`, `CONTRADICTED` and `ARCHIVED`. Pattern cases link immutable Observation and Evidence IDs and enforce uniqueness by observation and correlation identity within a Pattern. Contradicting cases are retained.

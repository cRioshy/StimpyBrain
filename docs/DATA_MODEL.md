# Data model

Observation schema v1 contains `observation_id`, `event_id`, `correlation_id`, `source`, `source_endpoint`, `source_type`, UTC observed/source timestamps, symbol, market, sanitized payload, deterministic SHA-256 content hash and schema version. SQLite metadata additionally records JSONL filename, byte offset, payload size, processing status and creation time.

Memory schema v1 contains the required identity/type/timestamps, source observation IDs, subject/relation/object, evidence and contradiction counts, bounded confidence, status, last verification, content and schema version. Allowed statuses are `OBSERVED`, `REPEATED`, `PROVISIONAL`, `SUPPORTED`, `CONTRADICTED`, `ARCHIVED`. Content explicitly records `causal=false`.

Workflow results contain their internal ID, observation foreign key, terminal status, reasons, gates and creation time. SQLite foreign keys are enabled for each store/repository connection.

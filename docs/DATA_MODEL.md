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

Phase-D.1 schema v7 adds:

- `hypotheses`: stable identity, bounded statement/question, creator, required data, status, confidence, supporting/contradicting/neutral counts and evaluation timestamps.
- `hypothesis_evidence`: append-only stable evidence linked to one Hypothesis, verified source Observation IDs, direction, strength, quality, description, timestamps and an independence key unique within the Hypothesis.
- `hypothesis_evaluations`: idempotent snapshots for an exact Evidence set and rule configuration, keeping Evidence Ratio separate from Confidence.

Hypothesis statuses are `NEW`, `INVESTIGATING`, `INCUBATING`, `PROVISIONAL`, `SUPPORTED`, `CONTRADICTED`, `REJECTED` and `ARCHIVED`. D.1 automatically emits only `NEW`, `INVESTIGATING`, `PROVISIONAL`, `SUPPORTED` or `CONTRADICTED`; later lifecycle phases own incubation, rejection and archival operations.

Phase-D.2 schema v8 adds:

- `hypothesis_reasoning`: immutable analysis for one exact Hypothesis Evaluation, with both sides, limitations, cautious non-causal conclusion, confidence and uncertainty.
- `hypothesis_critics`: one immutable review per Hypothesis Reasoning, including issues, suggestions, severity, bias warnings and calibration warning.
- `hypothesis_incubations`: initial Evaluation, Reasoning and Evidence identities, explicit status/due time, later new Evidence identities, final Evaluation/Reasoning and comparison deltas.

Incubation time alone changes no conclusion or confidence. Reactivation requires a due `READY` task and at least one independent Evidence identity absent from the initial snapshot. Both analyses survive restart.

Phase-D.3 schema v9 adds `hypothesis_lifecycle_events`. Every row stores a stable event ID, Hypothesis ID, `REJECT|ARCHIVE` action, previous and resulting status, bounded reason, actor and UTC timestamp. Events are append-only. The status change and audit insert occur in one SQLite transaction. `REJECTED` and `ARCHIVED` are terminal for evidence, evaluation, analysis and incubation reactivation; a rejected Hypothesis may only be archived for historical retention.

Schema v12 reserves isolated Shitzo research tables for lab runs, validated market events, frozen feature snapshots, decisions, accounts, positions, immutable closed trades, daily statistics, deduplicated research cases and review-only hypothesis suggestions. S.1 writes none of these operational records. Foreign keys and indexes establish the contract for later transactional repositories.

Schema v13 adds `peak_balance` to virtual accounts so maximum drawdown can be calculated against a persistent high-water mark. S.2 atomically closes a virtual position, appends its immutable trade and updates virtual balance, PnL, counters, peak and drawdown. Repeating the same close is idempotent.

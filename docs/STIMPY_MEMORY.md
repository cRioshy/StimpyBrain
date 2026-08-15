# Stimpy memory

Stimpy uses the existing `ObservationStore` and `MemoryService`; it does not create a competing memory file. Observations are append-only JSONL records with SQLite identity metadata. Relation memories retain source observation IDs, evidence and contradiction counts, bounded confidence, status and `causal=false`.

A single observation remains `OBSERVED`. Repetition may raise evidence count and confidence, while contradictory relations remain stored. The current service does not yet implement explicit short-, medium- and long-term memory partitions or temporal sequence tables; those remain later controlled phases.

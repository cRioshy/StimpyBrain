# Next steps

Completed: GET-only Pandorick client, verified endpoint allowlist, versioned normalizer, stable IDs/hashes, persistent deduplication, rotating JSONL and SQLite index, evidence memory, descriptive learning, internal shadow workflow, architecture graph, local GET-only API, worker lifecycle and Phase-2 test suite. Also completed: isolated local Observer/Memory/Evidence/Reasoning/Self-Critic/Knowledge prototype, stable Foundation result IDs, idempotent Evidence/Reasoning/Critic persistence, SQLite schema v4, bounded GET-only result projections and tests.

Next safe steps:

1. Design persistent `IncubationTask` storage and an explicitly triggered, testable reactivation service; do not connect it automatically to the worker.
2. Define cross-observation aggregation rules and minimum independent evidence counts before allowing knowledge promotion beyond `PROVISIONAL`.
3. Calibrate Evidence thresholds only against a reviewed, immutable offline dataset and keep score distinct from probability.
4. Review this implementation and explicitly approve activation before setting `STIMPY_PANDORICK_ENABLED=true`.
5. Add a cross-process singleton lock and orphan-JSONL reconciliation.
6. Ask the Pando project separately for a bounded read-only outcome endpoint if outcome ingestion is required; do not modify Pando from Stimpy work.

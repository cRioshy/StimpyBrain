# Next steps

Completed: GET-only Pandorick client, verified endpoint allowlist, versioned normalizer, stable IDs/hashes, persistent deduplication, rotating JSONL and SQLite index, evidence memory, descriptive learning, internal shadow workflow, architecture graph, local GET-only API, worker lifecycle and Phase-2 test suite. Also completed: Foundation result persistence, Phase-B Incubation and Phase-C Pattern Learning with SQLite schema v6, exact comparable-case grouping, market-regime separation, configurable minimum cases, contradiction retention, restart persistence and GET-only projection.

Next safe steps:

1. Design Phase-D Hypotheses as separate cautious records linked to supporting and contradicting Pattern IDs; do not promote Knowledge or change Pandorick automatically.
2. Define hypothesis minimum evidence, rejection and contradiction rules before implementation.
3. Calibrate Evidence and Pattern thresholds only against a reviewed, immutable offline dataset and keep scores distinct from probability.
4. Review this implementation and explicitly approve activation before setting `STIMPY_PANDORICK_ENABLED=true`.
5. Add a cross-process singleton lock and orphan-JSONL reconciliation.
6. Ask the Pando project separately for a bounded read-only outcome endpoint if outcome ingestion is required; do not modify Pando from Stimpy work.

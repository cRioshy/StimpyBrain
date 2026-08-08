# Next steps

Completed: GET-only Pandorick client, verified endpoint allowlist, versioned normalizer, stable IDs/hashes, persistent deduplication, rotating JSONL and SQLite index, evidence memory, descriptive learning, internal shadow workflow, architecture graph, local GET-only API, worker lifecycle and Phase-2 test suite. Also completed: Foundation result persistence, Phase-B Incubation, Phase-C Pattern Learning and Phase-D.1 Hypothesis foundation with SQLite schema v7, append-only evidence, independent-case deduplication, conservative evaluation and GET-only projections.

Next safe steps:

1. Design Phase D.2 Hypothesis-specific Reasoning and Self Critic records without reusing single-Observation semantics incorrectly.
2. Define an explicit Hypothesis incubation lifecycle that retains first evaluation and requires genuinely new independent Evidence before reactivation.
3. Calibrate Evidence, Pattern and Hypothesis thresholds only against a reviewed, immutable offline dataset and keep scores distinct from probability.
4. Review this implementation and explicitly approve activation before setting `STIMPY_PANDORICK_ENABLED=true`.
5. Add a cross-process singleton lock and orphan-JSONL reconciliation.
6. Ask the Pando project separately for a bounded read-only outcome endpoint if outcome ingestion is required; do not modify Pando from Stimpy work.

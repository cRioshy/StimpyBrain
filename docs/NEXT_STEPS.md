# Next steps

Completed: GET-only Pandorick client, verified endpoint allowlist, versioned normalizer, stable IDs/hashes, persistent deduplication, rotating JSONL and SQLite index, evidence memory, descriptive learning, internal shadow workflow, architecture graph, local GET-only API, worker lifecycle and Phase-2 test suite.

Next safe steps:

1. Re-authenticate GitHub CLI and create/use only a private `StimpyBrain` repository; never use Pando as a remote.
2. Review this implementation and explicitly approve activation before setting `STIMPY_PANDORICK_ENABLED=true`.
3. Add a cross-process singleton lock and orphan-JSONL reconciliation.
4. Ask the Pando project separately for a bounded read-only outcome endpoint if outcome ingestion is required; do not modify Pando from Stimpy work.
5. Diagnose the two slow Pandorick Rick endpoints before adding either to the polling allowlist.

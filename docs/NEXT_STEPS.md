# Next steps

Completed: GET-only Pandorick client, persistent observation/evidence foundations, Phase-B Incubation, Phase-C Pattern Learning, Phase-D.2 Hypothesis analysis and Phase-D.3 audited reject/archive lifecycle with SQLite schema v9. All network projections remain GET-only.

Next safe steps:

1. Calibrate Evidence, Pattern and Hypothesis thresholds only against a reviewed, immutable offline dataset and keep scores distinct from probability.
2. Design a local operator view for Hypotheses and lifecycle history without adding HTTP writes or unauthenticated controls.
3. Design future Inspiration or Knowledge Graph promotion as a separate reviewed phase with no automatic operational feedback.
4. Review this implementation and explicitly approve activation before setting `STIMPY_PANDORICK_ENABLED=true`.
5. Add a cross-process singleton lock and orphan-JSONL reconciliation.
6. Ask the Pando project separately for a bounded read-only outcome endpoint if outcome ingestion is required; do not modify Pando from Stimpy work.

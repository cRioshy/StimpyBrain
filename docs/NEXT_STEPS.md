# Next steps

Completed: GET-only Pandorick client, persistent observation/evidence foundations, Incubation, Pattern Learning, Hypothesis analysis, audited lifecycle and Phase-D.4 local read-only Hypothesis Controlcenter. All network projections remain GET-only.

Next safe steps:

1. Review E.1.1 replay cases, then design an explicit audited mapping into Hypothesis Evidence; never promote cases automatically.
2. Add bounded dashboard pagination only when more than 100 Hypotheses become a real local use case.
3. Design future Inspiration or Knowledge Graph promotion as a separate reviewed phase with no automatic operational feedback.
4. Review this implementation and explicitly approve activation before setting `STIMPY_PANDORICK_ENABLED=true`.
5. Add a cross-process singleton lock and orphan-JSONL reconciliation.
6. Ask the Pando project separately for a bounded read-only outcome endpoint if outcome ingestion is required; do not modify Pando from Stimpy work.

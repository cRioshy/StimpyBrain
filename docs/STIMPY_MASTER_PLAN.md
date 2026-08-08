# Stimpy master plan

StimpyBrain is the independent, read-only research system beside PandorickKi. Pandorick remains the operational analysis source; Stimpy stores observations, evaluates evidence, reasons cautiously, criticizes its own analysis and builds internal knowledge. A future external system named Ren may supervise both systems, but no Ren logic belongs in Stimpy.

## Non-negotiable boundary

The only permitted integration direction is `Pandorick GET API -> Stimpy`. Stimpy has no Pandorick write client, broker, order, Telegram, live-trading, self-modifying-code or automatic production-model replacement path.

## Controlled phases

1. **Foundation — completed:** observations, memory, configurable evidence rules, non-causal reasoning, Self Critic, provisional knowledge, stable IDs, SQLite schema v4 and GET-only projections.
2. **Incubation — completed:** persisted tasks, explicit idempotent reactivation, first/second analysis comparison, bounded failures and restart safety. No automatic worker connection.
3. **Pattern learning — completed:** explicit independent-case grouping, persisted case links, configurable minimum evidence, contradiction retention, market regimes and bounded GET-only projections. No automatic worker connection.
4. **Hypotheses — D.4 completed:** local bounded research questions, append-only Evidence, conservative evaluation, immutable Reasoning/Self Critic, explicit incubation, audited lifecycle and a responsive local read-only Controlcenter. Inspiration and graph integration remain separate reviewed phases.
5. **Strategy lab:** historical counterfactual simulation with strict look-ahead protection and separate storage.
6. **API and graph:** bounded domain projections and insights without raw-observation flooding.

Every phase requires targeted and full tests, documentation, BEFORE/AFTER backups and a Draft PR. A phase must not be described as AI or neural learning unless a future reviewed implementation actually provides that behavior.

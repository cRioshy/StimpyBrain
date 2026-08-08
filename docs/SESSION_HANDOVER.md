# Session handover

- Date/time: 2026-08-08 CEST.
- Goal: implement the minimal Phase D.1 Hypothesis foundation without Reasoning/Critic duplication, automatic data collection or Pandorick integration.
- Starting point: clean `agent/stimpy-pattern-learning` at `855299e`; baseline compile succeeded and 56/56 tests passed.
- Existing components reused: central Observation JSONL/SQLite store, persisted Observation identities, migration mechanism, configuration, app composition and GET-only API. Evidence/Reasoning/Critic/Incubation/Pattern/Knowledge components were not rewritten.
- Models added: `HypothesisStatus`, `HypothesisCreator`, `HypothesisEvidenceDirection`, validated `Hypothesis`, append-only `HypothesisEvidence` and immutable `HypothesisEvaluation`.
- Engine added: `HypothesisEngine` provides bounded stable creation, exact idempotency, verified Observation links, correlation-derived independence keys, supporting/contradicting/neutral Evidence and idempotent conservative evaluations.
- Evaluation: Evidence Ratio is weighted support divided by decisive weighted Evidence. Confidence separately combines consistency, mean quality, independent-case count and source diversity and is status-capped. It is not a price probability.
- Status rules: no Evidence is `NEW`; fewer than 25 cases is `INVESTIGATING`; at least 25 with ratio >=0.70 is `PROVISIONAL`; at least 25 with ratio <=0.30 is `CONTRADICTED`; `SUPPORTED` additionally requires at least 100 cases, mean quality >=0.60 and at least two sources. Three positive cases never become `SUPPORTED`.
- Storage: SQLite schema v7 adds `hypotheses`, append-only `hypothesis_evidence` and idempotent `hypothesis_evaluations`, with foreign keys, uniqueness constraints and indexes. Existing records are preserved.
- API: GET-only list, detail, Evidence and latest-evaluation projections were added. Hypothesis writes are local Python service calls only; all HTTP writes still return 405.
- Configuration: investigating/provisional/supported defaults 5/25/100, supported/contradicted ratios 0.70/0.30 and a 2,000-character text limit. These settings activate nothing automatically.
- Tests: targeted Hypothesis suite passed 9/9; full suite passed 65/65; `compileall`, environment configuration validation and SQLite foreign-key check succeeded with zero violations. The first targeted run had one incorrect boundary fixture (ratio 0.333 above the 0.30 contradiction threshold); the fixture was corrected. The first full run had only three expected schema-version assertions; all were updated and rerun successfully.
- Safety: no worker connection, network write endpoint, automatic collection, Pandorick write, broker, order, Telegram, live trading, strategy mutation, model update, code mutation or causal claim was added. Polling remains disabled by default.
- Not implemented: Hypothesis-specific Reasoning/Self Critic, incubation lifecycle, rejection/archive commands, Inspiration Engine, Mining/Social/On-Chain/Macro adapters, CLI and Knowledge Graph promotion.
- BEFORE backup: `C:\Users\testt\Desktop\StimpyBackUp_2026-08-08_12-16-14_BEFORE.zip`; 353,377 bytes and 315 entries; archive open and test extraction passed.
- AFTER backup: `C:\Users\testt\Desktop\StimpyBackUp_2026-08-08_12-29-06_AFTER.zip`; 424,793 bytes and 353 entries; archive open and test extraction passed.
- Git: branch `agent/stimpy-hypothesis-foundation`; implementation commit `6d7b3a4` (`Add Stimpy hypothesis foundation`) pushed to origin. Draft PR #6 targets `agent/stimpy-pattern-learning`: `https://github.com/cRioshy/StimpyBrain/pull/6`. Nothing was merged to `main`.
- Exact next safe step: design Phase D.2 immutable Hypothesis Reasoning and Self Critic records plus an explicit incubation lifecycle requiring new independent Evidence; do not alter Pandorick or promote Knowledge automatically.

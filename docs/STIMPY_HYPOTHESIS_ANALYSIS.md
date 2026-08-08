# Stimpy Hypothesis Analysis

Phase D.2 analyses an explicitly persisted `HypothesisEvaluation`; it does not reuse the older single-Observation reasoning semantics. `HypothesisAnalysisService.analyse()` creates one stable immutable `HypothesisReasoning` per exact evaluation and one associated `HypothesisCritic`. Repeated calls return the same records.

Reasoning always retains reasons, counterarguments, missing information, alternative explanations and assumptions. Its conclusion is explicitly non-causal. The Critic checks limited sample size, source diversity, missing counterexamples, causal wording and calibration. It also warns that look-ahead and data leakage have not been disproved by these descriptive records.

`create_incubation()` stores the initial Evaluation, Reasoning and exact Evidence identities and moves the Hypothesis to `INCUBATING`. `mark_ready()` is an explicit local call; no scheduler runs automatically. `reactivate()` succeeds only after the due time and only when at least one new independent Evidence identity exists. It stores a new Evaluation and Reasoning and compares status, Evidence Ratio, Confidence, case count and contradictions while preserving the initial records.

SQLite schema v8 stores these records in `hypothesis_reasoning`, `hypothesis_critics` and `hypothesis_incubations`. GET-only projections expose the latest analysis and critic plus bounded incubation lists. There are no HTTP writes, automatic data collection, worker activation, model updates, Knowledge promotion, Pandorick writes, broker calls, orders or Telegram messages.

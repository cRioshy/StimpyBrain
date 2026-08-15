# Stimpy Pattern Learning

Phase C implements deterministic, descriptive grouping of already persisted cases. It is not neural learning, does not estimate a winning probability and cannot change code, model weights, strategies, orders or Pandorick.

`PatternLearningService.learn()` is an explicit internal call. Each requested Observation must already exist and have a persisted Evidence result. A case is independent within its Pattern by correlation identity; repeated processing is idempotent. No worker, scheduler or HTTP write endpoint calls the service automatically.

The first grouping rule is deliberately narrow: `market + symbol + decision + market_regime`. Missing regimes become `UNKNOWN`; regime inference and indicator buckets are future reviewed work. `WIN` is positive, `LOSS` is negative, and all other outcomes are unresolved. Negative and unresolved cases remain stored in `pattern_cases`.

Default thresholds are 25 independent cases for `PROVISIONAL` or `CONTRADICTED`, and 50 entirely positive cases for `SUPPORTED`. Before the first threshold a Pattern remains `OBSERVED`. A negative majority at or above the threshold becomes `CONTRADICTED`; any negative case prevents `SUPPORTED`. Provisional and contradicted confidence is capped at 0.70, observed confidence below 0.50, and supported confidence at 0.90. This confidence is only a capped consistency score.

SQLite schema v6 stores aggregate `patterns` and immutable case links in `pattern_cases`. The GET-only `/api/stimpy/patterns` projection supports bounded pagination and status filtering and explicitly reports zero model updates and zero causal claims.

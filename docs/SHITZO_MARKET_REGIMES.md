# Shitzo market regimes

Shitzo classifies each frozen feature snapshot at decision time. The classifier is deterministic and uses only the snapshot's short/long moving averages, momentum and volatility; it never reads future prices or changes a strategy decision.

Version `shitzo-regime-v1` uses fixed, frozen thresholds: MA spread `0.0002`, low volatility `0.0001`, and high volatility `0.0005`. Trend labels are `UP_TREND`, `DOWN_TREND`, `RANGE`, or `INSUFFICIENT_DATA`. Volatility labels are `LOW_VOLATILITY`, `NORMAL_VOLATILITY`, `HIGH_VOLATILITY`, or `INSUFFICIENT_DATA`.

Schema v16 stores labels separately in `shitzo_regime_labels`, uniquely keyed by snapshot and classifier version. Existing snapshots can be classified idempotently as `HISTORICAL_BACKFILL`; live labels use `LIVE`. Original snapshots and decisions are not rewritten by backfill.

GET-only API projections expose labels, current regimes, distribution, strategy performance by entry regime, and loss details. Small groups are marked `INSUFFICIENT_CASES` until five closed trades exist. These figures are descriptive paper-trading research, not predictions or trading signals.

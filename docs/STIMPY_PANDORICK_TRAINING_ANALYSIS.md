# Pandorick training analysis (E.1.2)

`PandorickTrainingService` imports only the current `platform_decisions.jsonl` and `trade_outcomes.jsonl` entries from a reviewed ZIP. It accepts BTCUSDT, ETHUSDT and XRPUSDT decisions with valid prices, keeps only the final closed outcome per decision and creates a chronological 60/20/20 split.

The immutable SQLite run, cases and metrics cover confidence calibration, error combinations, volatility, volume and market regime. Re-importing the same archive is idempotent. Results are descriptive paper-trade research: they do not promote Hypothesis evidence, mutate models, place orders or write to Pandorick.

The 2026-08-08 run linked 1,402 cases from 16,710 eligible decisions. Its 281-case test split had a 33.8% win rate, 63.3% average confidence and a -29.5 percentage-point calibration gap. High-volume cases were only 21 observations with 9.5% wins. Volatility was entirely LOW and regimes were almost entirely STRONG_UP, so neither dimension is currently varied enough for a robust conclusion. All outcomes were LONG and the sample covers only a short period; no predictive or causal claim is justified.

GET-only projections are available at `/api/stimpy/training-runs` and `/api/stimpy/training-runs/{run_id}/metrics`. The Controlcenter shows the latest test summary.

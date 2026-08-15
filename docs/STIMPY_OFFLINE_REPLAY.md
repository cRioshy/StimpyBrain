# Stimpy Offline Replay E.1.1

`OfflineReplayService.run_csv()` reads a local UTF-8 OHLCV CSV with `timestamp,open,high,low,close,volume`. Rows must be finite, valid and strictly chronological. Files are bounded to 100 MB and require at least 30 rows.

The service calculates MA5/10/20, rolling volatility, volume context and local highs using current and earlier rows only. Ten transparent technical rule keys cover trend, overextension, breakout, false breakout, retest, volatility, volume, multi-timeframe proxy, market regime and time dependence. Outcomes are measured only after the configured horizon.

Data is split chronologically into 60% TRAIN, 20% VALIDATION and 20% TEST. A case is discarded if its outcome crosses a split boundary. Dataset bytes plus configuration produce a stable run ID, so identical reruns are idempotent.

SQLite schema v10 stores immutable `replay_runs` and `replay_cases`. GET-only projections are `/api/stimpy/replay-runs` and `/api/stimpy/replay-runs/{id}/cases`. E.1.1 does not automatically convert cases into confirmed Hypothesis Evidence, tune thresholds, create orders or connect to Pandorick.

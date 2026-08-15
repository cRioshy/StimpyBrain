# Stimpy evidence

`EvidenceEngine` applies centrally configured, transparent heuristic points. The raw score and normalized score are not probabilities. Foundation schema v4 stores one stable `EvidenceResult` per observation with supporting and contradicting evidence, evidence count, an independent quality score, UTC creation time and schema version.

Current quality distinguishes final outcomes from `OPEN` or `UNKNOWN`. Source calibration, comparable-case counts, drawdown, regimes and timeframe quality are not yet implemented. Reprocessing the same observation reuses the stored result rather than silently replacing it.

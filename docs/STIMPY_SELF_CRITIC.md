# Stimpy Self Critic

The Self Critic checks possible confidence miscalibration, high-confidence losses, large negative results, inconsistent outcome/profit semantics and unresolved outcomes. It emits cautious issues, suggestions, a calibration warning and one of `INFO`, `LOW`, `MEDIUM`, `HIGH` or `CRITICAL`.

Critic results have stable critic, observation and reasoning IDs and are persisted idempotently. The critic cannot change rules, weights, Pandorick decisions or execution behavior.

# Known problems

- `KP-S2-001`: Pandorick `/api/v1/learning/summary` and `/api/v1/graph/overview` exceeded the 5-second live verification timeout. They are not polled.
- `KP-S2-002`: Pandorick has no verified `/api/v1/outcomes/recent`; outcome linking works for normalized synthetic/future outcome observations but no source is connected.
- `KP-S2-003`: Stimpy API has no authentication. It is forced to `127.0.0.1` and should not be exposed externally.
- `KP-S2-004`: single-worker enforcement is within one Python process. Starting two independent OS processes is not yet protected by a robust stale-lock protocol.
- `KP-S2-005`: an orphan JSONL line can remain if disk append succeeds but SQLite insertion fails. It is not indexed or processed, but repair/compaction tooling is not implemented.
- `KP-S2-006`: Phase-2 memory supports evidence relations and contradictions but does not yet maintain a dedicated temporal-sequence table.
- `KP-RP-001`: prototype Evidence rules are illustrative fixed thresholds and have not been statistically calibrated.
- `KP-RP-002`: knowledge entries still represent individual observations only. Phase-C Patterns do not automatically promote or rewrite Knowledge entries.
- `KP-B-001`: incubation persistence and explicit reactivation exist, but no scheduler or worker integration exists by design. An operator or future reviewed coordinator must call readiness/reactivation explicitly.
- `KP-B-002`: Phase B compares two already persisted single-observation Reasoning results. Multi-observation evidence aggregation belongs to Pattern Learning and is not implied by incubation.
- `KP-RP-004`: a caller that omits both an upstream observation ID and timestamp receives a content-stable ID; repeated identical content is intentionally treated as a duplicate.
- `KP-A2-001`: Foundation result IDs are stable and persisted, but the isolated prototype is intentionally not connected to the worker. Automatic processing requires a separate reviewed integration phase.
- `KP-A2-002`: Evidence quality currently distinguishes final from unresolved outcomes only. Broader source-quality, freshness and comparable-case calibration are future offline work.
- `KP-C-001`: Pattern grouping currently uses exact market, symbol, decision and caller-supplied market-regime labels. Indicator bucketing and regime inference are not implemented.
- `KP-C-002`: Pattern confidence is an explainable capped consistency score, not a calibrated probability. Thresholds require later review against an immutable offline dataset.
- `KP-C-003`: Pattern Learning is intentionally explicit and not connected to the worker. Concurrent independent service callers are not an intended activation mode.

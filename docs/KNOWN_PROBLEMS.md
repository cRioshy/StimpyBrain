# Known problems

- `KP-S2-001`: Pandorick `/api/v1/learning/summary` and `/api/v1/graph/overview` exceeded the 5-second live verification timeout. They are not polled.
- `KP-S2-002`: Pandorick has no verified `/api/v1/outcomes/recent`; outcome linking works for normalized synthetic/future outcome observations but no source is connected.
- `KP-S2-003`: Stimpy API has no authentication. It is forced to `127.0.0.1` and should not be exposed externally.
- `KP-S2-004`: single-worker enforcement is within one Python process. Starting two independent OS processes is not yet protected by a robust stale-lock protocol.
- `KP-S2-005`: an orphan JSONL line can remain if disk append succeeds but SQLite insertion fails. It is not indexed or processed, but repair/compaction tooling is not implemented.
- `KP-S2-006`: Phase-2 memory supports evidence relations and contradictions but does not yet maintain a dedicated temporal-sequence table.
- `KP-RP-001`: prototype Evidence rules are illustrative fixed thresholds and have not been statistically calibrated.
- `KP-RP-002`: knowledge entries represent individual observations only; cross-observation support/contradiction promotion is not implemented, so the prototype never produces `SUPPORTED`.
- `KP-RP-003`: incubation is a typed interface only. Persistence, scheduling, reactivation and comparison do not yet exist.
- `KP-RP-004`: a caller that omits both an upstream observation ID and timestamp receives a content-stable ID; repeated identical content is intentionally treated as a duplicate.
- `KP-A2-001`: Foundation result IDs are stable and persisted, but the isolated prototype is intentionally not connected to the worker. Automatic processing requires a separate reviewed integration phase.
- `KP-A2-002`: Evidence quality currently distinguishes final from unresolved outcomes only. Broader source-quality, freshness and comparable-case calibration are future offline work.

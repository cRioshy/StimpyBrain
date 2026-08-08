# Security boundaries

- Pando and Stimpy are separate repositories and processes.
- Stimpy accepts only loopback Pandorick URLs and exposes only a loopback API.
- The source client implements GET only; writes are blocked before transport.
- Polling defaults to disabled and mode is permanently `observe`/read-only.
- No broker, order, Telegram or Decision-Core feedback code exists.
- Responses are schema-checked, size-bounded, recursively redacted, finite-number checked and timestamp checked.
- JSONL is append-only; SQLite provides persistent identity indexes and foreign keys.
- Workflow results are internal, terminal-only and always have zero order side effects.
- Evidence, Reasoning and Critic projections are internal, GET-only and cannot authorize an order or write to Pandorick.
- Incubation is explicit and local: no background scheduler, worker activation, network callback or confidence increase without new persisted evidence.
- Pattern Learning is explicit and local: it requires persisted Evidence, preserves contradictions, cannot update models or strategies and has no automatic worker activation.
- Hypotheses are explicit local research artifacts: bounded text, verified Observation links, append-only Evidence, zero causal claims and no automatic data collection, worker activation, model update or strategy change.
- Hypothesis HTTP projections are GET-only. Creating, adding Evidence and evaluating are not network write operations.
- Hypothesis Reasoning, Critic and incubation are local and deterministic. Reactivation requires new independent persisted Evidence; elapsed time alone cannot improve a result.
- No scheduler, worker, Inspiration Engine or Knowledge promotion is connected to D.2.
- Reject/archive commands require bounded non-secret reason and actor text, execute locally and store an immutable audit event atomically with the status change.
- Terminal Hypotheses fail closed against later Evidence, evaluation, analysis and incubation reactivation. Lifecycle writes are not exposed through HTTP.
- `.env`, databases, observation data, logs, ZIPs, virtual environments and caches are ignored by Git.

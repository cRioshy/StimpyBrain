# Security boundaries

- Pando and Stimpy are separate repositories and processes.
- Stimpy accepts only loopback Pandorick URLs and exposes only a loopback API.
- The source client implements GET only; writes are blocked before transport.
- Polling defaults to disabled and mode is permanently `observe`/read-only.
- No broker, order, Telegram or Decision-Core feedback code exists.
- Responses are schema-checked, size-bounded, recursively redacted, finite-number checked and timestamp checked.
- JSONL is append-only; SQLite provides persistent identity indexes and foreign keys.
- Workflow results are internal, terminal-only and always have zero order side effects.
- `.env`, databases, observation data, logs, ZIPs, virtual environments and caches are ignored by Git.

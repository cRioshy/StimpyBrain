# Next steps

1. Agree a versioned, one-way Pandorick event envelope and transport without modifying Pandorick.
2. Add contract fixtures for every allowlisted topic, including outcomes and malformed payloads.
3. Design authenticated read-only HTTP endpoints only if a network API is actually required.
4. Define backup, retention, and explicit SQLite migration procedures before production data.
5. Add load and process-crash recovery tests; keep live trading technically impossible.

Completed: standalone structure, strict workflow topology, terminal-only persistence, sanitizer, observation memory/learning projections, knowledge graph, read-only facade, and initial safety tests.

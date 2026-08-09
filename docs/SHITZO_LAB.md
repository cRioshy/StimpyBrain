# Shitzo research lab

Shitzo is an isolated, disabled-by-default paper-trading research foundation inside StimpyBrain. It can never authorize or place real orders. Phase S.1 contains only immutable validated models, a capability-minimal read-only feed protocol, a bounded chronological Price Window, a frozen Feature Snapshot and the SQLite schema needed by later reviewed phases.

Supported Phase-1 symbols are `BTC-USD`, `ETH-USD` and `XRP-USD`. A tick requires a finite positive price, UTC-normalized aware timestamp, source and unique source event identity. The Price Window rejects non-chronological data, deduplicates events, requires a complete long window and freezes source identities, time bounds, moving averages, momentum and volatility in a stable content-derived snapshot.

No live provider, network client, trader, PaperBroker, account mutation, position processing, Evidence Bridge, Hypothesis Suggestion service, API route, Controlcenter integration or worker activation exists in S.1. Schema v12 reserves logically separate `shitzo_*` tables so later work can remain restart-safe and append-oriented in Stimpy's single SQLite database.

Security is structural: `MarketDataFeed` exposes only `source_name` and `read_latest`; a validator rejects write-capable objects. Tests inspect the package AST for trading calls and network/trading dependencies. `SHITZO_ENABLED=false` is the permanent default until a later separately reviewed activation. There is no profit guarantee and all future activity must remain virtual research.

Next reviewed phases are: S.2 PaperBroker/repository transactions, S.3 deterministic traders, S.4 bounded lab orchestration/GET projections, and only then S.5 Evidence/Pattern bridging. A concrete public read-only market-data provider must be selected before any live feed implementation.

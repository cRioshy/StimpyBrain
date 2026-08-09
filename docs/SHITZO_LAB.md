# Shitzo research lab

Shitzo is an isolated, disabled-by-default paper-trading research laboratory inside StimpyBrain. It can never authorize or place real orders. Phase S.2 adds a deterministic purely virtual PaperBroker and transactional repository to the S.1 models, read-only feed protocol and frozen Price Window.

Supported Phase-1 symbols are `BTC-USD`, `ETH-USD` and `XRP-USD`. A tick requires a finite positive price, UTC-normalized aware timestamp, source and unique source event identity. The Price Window rejects non-chronological data, deduplicates events, requires a complete long window and freezes source identities, time bounds, moving averages, momentum and volatility in a stable content-derived snapshot.

The PaperBroker handles LONG/SHORT virtual PnL, WAIT and Confidence gates, balance-capped sizing, Stop-Loss, Take-Profit, manual test closure and one open position per trader/symbol. Position closure, immutable trade creation and account statistics update occur in one transaction. Open positions survive restart. Schema v13 persists the account high-water mark for drawdown.

No live provider, network client, strategy trader, Evidence Bridge, Hypothesis Suggestion service, API route, Controlcenter integration or worker activation exists. No position is closed merely because Stimpy stops.

Security is structural: `MarketDataFeed` exposes only `source_name` and `read_latest`; a validator rejects write-capable objects. Tests inspect the package AST for trading calls and network/trading dependencies. `SHITZO_ENABLED=false` is the permanent default until a later separately reviewed activation. There is no profit guarantee and all future activity must remain virtual research.

Next reviewed phases are: S.3 deterministic traders, S.4 bounded lab orchestration/GET projections, and only then S.5 Evidence/Pattern bridging. A concrete public read-only market-data provider must be selected before any live feed implementation.

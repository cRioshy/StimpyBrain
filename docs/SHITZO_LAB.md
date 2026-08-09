# Shitzo research lab

Shitzo is an isolated, disabled-by-default paper-trading research laboratory inside StimpyBrain. It can never authorize or place real orders. Phase S.3 adds deterministic Trend, Momentum and Contrarian research traders to the virtual S.2 broker and repository.

Supported Phase-1 symbols are `BTC-USD`, `ETH-USD` and `XRP-USD`. A tick requires a finite positive price, UTC-normalized aware timestamp, source and unique source event identity. The Price Window rejects non-chronological data, deduplicates events, requires a complete long window and freezes source identities, time bounds, moving averages, momentum and volatility in a stable content-derived snapshot.

The PaperBroker handles LONG/SHORT virtual PnL, WAIT and Confidence gates, balance-capped sizing, Stop-Loss, Take-Profit, manual test closure and one open position per trader/symbol. Position closure, immutable trade creation and account statistics update occur in one transaction. Open positions survive restart. Schema v13 persists the account high-water mark for drawdown.

`shitzo-trend` compares short and long moving averages. `shitzo-momentum` evaluates frozen window momentum. `shitzo-contrarian` compares price with the long mean and deliberately takes the opposite direction beyond its threshold. Each emits LONG, SHORT or WAIT with a transparent reason, stable identity and Confidence capped at 0.75. These are experiments, not profitable-strategy claims.

No live provider, network client, Evidence Bridge, Hypothesis Suggestion service, API route, Controlcenter integration or worker activation exists. No position is closed merely because Stimpy stops.

Security is structural: `MarketDataFeed` exposes only `source_name` and `read_latest`; a validator rejects write-capable objects. Tests inspect the package AST for trading calls and network/trading dependencies. `SHITZO_ENABLED=false` is the permanent default until a later separately reviewed activation. There is no profit guarantee and all future activity must remain virtual research.

Next reviewed phases are: S.4 bounded lab orchestration/GET projections, and only then S.5 Evidence/Pattern bridging. A concrete public read-only market-data provider must be selected before any live feed implementation.

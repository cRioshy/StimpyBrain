# Shitzo research lab

Shitzo is an isolated, disabled-by-default paper-trading research laboratory inside StimpyBrain. It can never authorize or place real orders. Phase S.4 adds explicit bounded tick orchestration and GET-only projections to the virtual broker and deterministic traders.

Supported Shitzo symbols are `BTC-USD`, `ETH-USD`, `XRP-USD`, `SOL-USD`, `ADA-USD` and `DOGE-USD`. A tick requires a finite positive price, UTC-normalized aware timestamp, source and unique source event identity. The Price Window rejects non-chronological data, deduplicates events, requires a complete long window and freezes source identities, time bounds, moving averages, momentum and volatility in a stable content-derived snapshot.

The PaperBroker handles LONG/SHORT virtual PnL, WAIT and Confidence gates, balance-capped sizing, Stop-Loss, Take-Profit, optional maximum holding time, manual test closure and one open position per trader/symbol. A time-limited close records the actual current virtual PnL as WIN/LOSS/NEUTRAL. Position closure, immutable trade creation and account statistics update occur in one transaction. Open positions survive restart. Schema v13 persists the account high-water mark for drawdown.

`shitzo-trend` compares short and long moving averages. `shitzo-momentum` evaluates frozen window momentum. `shitzo-contrarian` compares price with the long mean and deliberately takes the opposite direction beyond its threshold. Each emits LONG, SHORT or WAIT with a transparent reason, stable identity and Confidence capped at 0.75. These are experiments, not profitable-strategy claims.

After the reviewed one-hour all-WAIT run, the operator explicitly approved half entry thresholds: Trend 0.0005 (0.05%), Momentum 0.0015 (0.15%) and Contrarian 0.0025 (0.25%). Strategy versions include `half-threshold` so later outcomes remain distinguishable from the original rules. Risk, minimum Confidence, Stop-Loss and Take-Profit are unchanged.

`ShitzoLab` must be explicitly enabled and started locally. It creates virtual accounts, accepts validated ticks one at a time, updates open positions, freezes complete windows, asks each trader for a decision and passes eligible decisions to the virtual PaperBroker. It owns no thread or network client. The separate `ShitzoCollector` can continuously call it through the credential-free Coinbase Exchange GET ticker when `SHITZO_ENABLED=true` and `SHITZO_AUTORUN=true`. Stopping records the run state but preserves open positions.

GET-only status, trader, account, position, decision and trade projections are displayed as a compact read-only Controlcenter summary, including tick and feed-error counters. There are no buttons or HTTP writes. No Evidence Bridge, Hypothesis Suggestion service or real-order path exists.

Security is structural: `MarketDataFeed` exposes only `source_name` and `read_latest`; a validator rejects write-capable objects. Tests inspect the package AST for trading calls and network/trading dependencies. `SHITZO_ENABLED=false` is the permanent default until a later separately reviewed activation. There is no profit guarantee and all future activity must remain virtual research.

The next reviewed phase is S.5 Evidence/Pattern bridging. A concrete public read-only market-data provider must still be selected before any live feed implementation.

# Session handover

## Shitzo half-threshold experiment — 2026-08-10

- After a completed one-hour live-paper run produced 5,643 WAIT decisions and zero trades, the operator explicitly approved half strategy entry thresholds.
- New defaults: Trend 0.0005, Momentum 0.0015, Contrarian 0.0025. Strategy versions now carry `half-threshold` for auditable outcome separation.
- Risk, minimum Confidence, virtual Stop-Loss/Take-Profit, no-leverage cap and all no-real-order boundaries remain unchanged. More false entries and virtual losses are expected and accepted as research data.
- Verified BEFORE backup: `C:\Users\testt\Desktop\StimpyBackUp_2026-08-10_20-37-58_BEFORE_HALF_THRESHOLDS.zip`.

## Controlled Shitzo fixture run — 2026-08-10

- Explicit local run `controlled-fixture-20260810-1910` used generated BTC-USD, ETH-USD and XRP-USD ticks only; no internet/provider was used. Risk was temporarily 0.001 inside the script.
- Result: STOPPED, 3 virtual accounts, 18 decisions, 18 closed virtual trades, 6 WIN / 3 LOSS / 9 NEUTRAL, total realized PnL +76.545633 USD and zero open positions. Nine remaining positions were explicitly `MANUAL_TEST_CLOSE`.
- Foreign-key check passed. Shitzo returned to `enabled=false`, `active=false`, `automatic=false`, `live_provider=false`, `real_orders=false`.
- The run exposed and fixed a GET projection counter bug: filtered OPEN position totals now match filtered items (0/0). Targeted S.4 tests 4/4 passed.
- Verified pre-run backup: `C:\Users\testt\Desktop\StimpyBackUp_2026-08-10_19-06-30_BEFORE_CONTROLLED_RUN.zip`.
- Planned post-run backup: `C:\Users\testt\Desktop\StimpyBackUp_2026-08-10_19-08-04_AFTER_CONTROLLED_RUN.zip`.

## Shitzo Phase S.4 update — 2026-08-10

- Added explicit `ShitzoLab` orchestration: local start, one validated tick at a time, position update, frozen window, three decisions, virtual broker and persistence. No thread, timer or provider exists.
- Disabled and unstarted calls fail closed. `build_app()` composes but never starts Shitzo. Lab stop preserves open positions and records STOPPED state.
- Added bounded GET-only status, traders, accounts, positions, decisions and trades endpoints plus a responsive read-only Controlcenter summary. All HTTP writes remain 405.
- No real broker/order, credentials, network feed, Stimpy-worker connection, Evidence bridge, model mutation or automatic activation was added. Schema remains v13.
- Targeted Lab/API tests 4/4, combined S.4/Controlcenter tests 6/6 and full suite 102/102 passed; JavaScript syntax, Python compile and diff checks passed. One earlier full run hit its 120-second command limit; the verbose rerun completed successfully in 105 seconds.
- Verified BEFORE backup: `C:\Users\testt\Desktop\StimpyBackUp_2026-08-10_18-49-54_BEFORE.zip` (804,138 bytes, 168 entries).
- Planned verified AFTER backup: `C:\Users\testt\Desktop\StimpyBackUp_2026-08-10_19-03-45_AFTER.zip`.
- Branch: `agent/stimpy-shitzo-lab-api`. Next safe step: controlled fixture/replay inspection, then separately reviewed S.5 research-case Evidence bridge.

## Shitzo Phase S.3 update — 2026-08-09

- Added capability-free deterministic `shitzo-trend`, `shitzo-momentum` and `shitzo-contrarian` traders operating only on immutable FeatureSnapshots.
- Each strategy returns stable LONG/SHORT/WAIT decisions with transparent numeric reasons, configurable positive thresholds and Confidence capped at 0.75. Missing snapshots fail with `InsufficientDataError`.
- Added environment threshold defaults: trend 0.001, momentum 0.003 and contrarian 0.005.
- No provider, network dependency, repository/broker access inside traders, worker, API, UI, Evidence bridge or automatic activation was added. Schema remains v13 and `SHITZO_ENABLED=false`.
- Targeted Shitzo tests 14/14 and full suite 98/98 passed; compile and diff checks passed.
- Verified BEFORE backup: `C:\Users\testt\Desktop\StimpyBackUp_2026-08-09_20-46-24_BEFORE.zip` (789,667 bytes, 156 entries).
- Planned verified AFTER backup: `C:\Users\testt\Desktop\StimpyBackUp_2026-08-09_20-51-45_AFTER.zip`.
- Branch: `agent/stimpy-shitzo-traders`. Next safe step: explicit bounded S.4 orchestration and GET-only projections.

## Shitzo Phase S.2 update — 2026-08-09

- Added purely virtual `PaperBroker`, validated PaperPosition/TraderAccount/outcome enums and `ShitzoRepository` with atomic virtual close/trade/account updates.
- Supports virtual LONG/SHORT PnL, WAIT and Confidence rejection, balance-capped sizing, Stop-Loss, Take-Profit, manual test close, idempotent closure and one open position per trader/symbol.
- Schema v13 adds persistent account high-water balance for maximum drawdown; live database migration passed with zero foreign-key errors and zero operational Shitzo rows.
- No network client, provider, trader, worker, API route, Evidence bridge, real broker, real order or activation was added. `SHITZO_ENABLED=false` remains unchanged.
- Targeted S.1/S.2 tests 10/10 and full suite 94/94 passed; compile and diff checks passed.
- Verified BEFORE backup: `C:\Users\testt\Desktop\StimpyBackUp_2026-08-09_20-37-08_BEFORE.zip` (764,668 bytes, 150 entries).
- Planned verified AFTER backup: `C:\Users\testt\Desktop\StimpyBackUp_2026-08-09_20-45-22_AFTER.zip`.
- Branch: `agent/stimpy-shitzo-paper-broker`. Next safe step: deterministic frozen-snapshot traders in S.3.

## Shitzo Phase S.1 update — 2026-08-09

- Added isolated `stimpy/shitzo` foundation: strict MarketTick/TraderDecision/FeatureSnapshot records, capability-minimal read-only feed protocol and bounded chronological Price Window with stable frozen snapshots.
- SQLite schema v12 reserves ten logically separated `shitzo_*` tables with foreign keys and query indexes. No Shitzo operational data is written in S.1.
- `SHITZO_ENABLED=false` by default; only BTC-USD, ETH-USD and XRP-USD are accepted.
- Deliberately absent: live provider, networking, traders, PaperBroker, worker, API/UI integration, Evidence bridge and automatic Hypothesis promotion.
- Security tests reject write-capable feeds and scan the package AST for broker/order/transfer calls and networking/trading dependencies.
- Baseline 84/84; S.1 targeted 5/5; full suite 89/89 passed. Compile and diff checks passed before documentation.
- Verified BEFORE backup: `C:\Users\testt\Desktop\StimpyBackUp_2026-08-09_20-20-08_BEFORE.zip` (739,053 bytes, 139 entries; database/source/tests present).
- Planned verified AFTER backup: `C:\Users\testt\Desktop\StimpyBackUp_2026-08-09_20-26-36_AFTER.zip`.
- Branch: `agent/stimpy-shitzo-foundation`. Next safe step: choose a public read-only provider, then implement S.2 virtual broker/repository separately.

## Phase E.1.2 update — 2026-08-08

- Added filtered, idempotent Pandorick ZIP analysis for confidence calibration, errors, volatility, volume and market regime, persisted in SQLite schema v11.
- The reviewed archive produced 1,402 linked final crypto cases; the 281-case test split had 33.8% wins, 63.3% average confidence and a -29.5 point calibration gap.
- Limitations: LONG-only outcomes, short date range, LOW-volatility and STRONG_UP concentration; results are descriptive paper simulation, not predictions or evidence promotion.
- Added GET-only run/metric projections and a latest-run summary in the local Controlcenter.
- Tests: targeted 5/5 and full suite 84/84 passed; JavaScript syntax, Python compile and diff checks passed.
- BEFORE backup: `C:\Users\testt\Desktop\StimpyBackUp_2026-08-08_22-31-48_BEFORE.zip` (916,619 bytes, 555 entries).
- Branch: `agent/stimpy-pandorick-training-analysis`; exact next safe step is collecting longer, varied and direction-balanced market data before reviewed evidence mapping.

## Phase E.1.1 update — 2026-08-08

- Added explicit local `OfflineReplayService` for bounded chronological OHLCV CSV files and ten transparent technical rule keys.
- Added strict OHLCV/time validation, stable dataset/run identities, 60/20/20 chronological splits and prevention of outcome leakage across split boundaries.
- SQLite schema v10 adds immutable `replay_runs` and `replay_cases`; GET-only run/case projections were added and `build_app()` exposes `offline_replay`.
- Replay cases are research outputs only and are not automatically promoted into the 20 Hypotheses, Knowledge or trading behavior.
- Tests: replay 3/3 and full suite 82/82 passed; compile and diff checks passed. The first targeted run exposed one SQL placeholder mismatch, which was fixed. The first full run required six expected schema assertions to move from 9 to 10.
- Verified BEFORE backup including the live database and 20 Hypotheses: `C:\Users\testt\Desktop\StimpyBackUp_2026-08-08_21-09-22_BEFORE.zip` (848,193 bytes, 528 entries). An earlier partial archive at `...21-08-22_BEFORE.zip` is not the authoritative backup.
- Branch: `agent/stimpy-offline-replay`, based on D.4. Exact next step: run a reviewed real BTCUSD 15-minute CSV, inspect cases, then design explicit Evidence promotion.

- Date/time: 2026-08-08 CEST.
- Goal: implement Phase D.4 local responsive read-only Hypothesis Controlcenter without adding unauthenticated write controls.
- Starting point: clean `agent/stimpy-hypothesis-lifecycle` at `8df5cc6`; baseline compile succeeded and 76/76 tests passed.
- Branch: `agent/stimpy-hypothesis-controlcenter`, based on `agent/stimpy-hypothesis-lifecycle`.
- UI added: packaged dependency-free HTML/CSS/JavaScript at `/controlcenter`, served by the existing loopback API server.
- Contents: status summary, search/status filter, Hypothesis list and detail with Confidence, uncertainty, Evidence Ratio, independent cases, Reasoning, counterarguments, missing information, alternatives, Self Critic, Evidence, incubation and lifecycle history.
- Refresh: explicit refresh button plus GET-only 15-second polling of bounded existing projections. Empty, loading and connection-error states are visible.
- Responsive/accessibility: flexible grids, small-screen single-column layout, semantic regions/labels, keyboard-focus styles, reduced-motion respect and no fixed page width.
- Security: no forms or lifecycle controls, no write request, no external dependencies, persisted values inserted as text nodes, restrictive Content Security Policy, `nosniff` and `no-store`. Unknown asset paths return 404; all HTTP writes remain 405.
- Storage: unchanged at SQLite schema v9; the Controlcenter performs no migrations or mutations.
- Tests: targeted Controlcenter suite passed 3/3; full suite passed 79/79; Python compile, JavaScript syntax check and `git diff --check` succeeded.
- Safety: no automatic decision, network write, Pandorick write, broker, order, Telegram, live trading, strategy/model/code mutation, Knowledge promotion or causal claim was added. Polling remains disabled by default.
- Limitations: the view loads bounded pages of at most 100 records and has no pagination UI. It must remain loopback-only because the API has no authentication.
- BEFORE backup: `C:\Users\testt\Desktop\StimpyBackUp_2026-08-08_16-44-46_BEFORE.zip`; 771,877 bytes and 487 entries; archive open and test extraction passed.
- Git/PR: implementation commit `d684c6b` (`Add read-only hypothesis controlcenter`) pushed on `agent/stimpy-hypothesis-controlcenter`. Draft PR #9 targets `agent/stimpy-hypothesis-lifecycle`: `https://github.com/cRioshy/StimpyBrain/pull/9`. Nothing was merged to `main`.
- AFTER backup: `C:\Users\testt\Desktop\StimpyBackUp_2026-08-08_16-51-56_AFTER.zip`; created after final handover commit and verified by archive open plus test extraction.
- Exact next safe step: collect and review an immutable offline calibration dataset; add dashboard pagination only when local record volume requires it.

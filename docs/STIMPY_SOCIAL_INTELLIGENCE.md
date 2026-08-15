# Stimpy Social Intelligence

## Boundary and flow

The disabled-by-default Social Influence Observer reads configured public X posts through the official X API v2. Its flow is `SocialObserverWorker -> XReadOnlyAdapter -> SocialClassifier -> SocialRepository -> SocialResearchService -> GET API/Controlcenter`. It observes temporal associations only and cannot publish, like, follow, message, place orders, contact a broker, call Telegram or write to Pandorick.

## Configuration

Enablement requires `STIMPY_SOCIAL_ENABLED=true`, `STIMPY_SOCIAL_PLATFORM_X_ENABLED=true`, `STIMPY_SOCIAL_ACCOUNTS` and `X_BEARER_TOKEN`. Optional bounded variables control polling, posts per account, text size, reaction windows and hypothesis minimum cases. Credentials remain in process memory and are never stored or logged. Without them the status is `DISABLED_NO_CREDENTIALS`.

## Models, audit and storage

Rules produce topics, asset mappings, relevance, sentiment, intensity, reasons and classifier version. Stable platform/post identity prevents repeated processing; normalized text hashes group same-text posts. Ignored posts remain visible. SQLite schema v14 stores posts, events, frozen market snapshots, reaction analyses, descriptive profiles, candidate hypotheses and worker state in the existing database.

`SocialResearchService` accepts frozen `T-30m`, `T-5m`, `T0`, `+5m`, `+30m`, `+2h`, and `+24h` snapshots. Later data appends evidence without changing the original classification. Profiles are labeled `Historical Influence Association`; suggestions require the configured minimum case count and remain `NEW`, never automatically promoted or connected to trading.

## API and Controlcenter

Bounded GET routes under `/api/stimpy/social/` expose status, feed, interesting posts, post detail, accounts, reactions, influence and hypotheses. The responsive `SOCIAL INTELLIGENCE` view includes ignored posts, watchlist, audit reasons and the explicit warning that temporal association is not causality. Every HTTP write method returns 405.

## Limits

Phase 1 contains a restart-safe explicit reaction recorder, not an unattended historical-candle scheduler. X access tier, retention/deletion duties and a licensed historical candle provider must be reviewed before live unattended research. No fixture is presented as a real post.

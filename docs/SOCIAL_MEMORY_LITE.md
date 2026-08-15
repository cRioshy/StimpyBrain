# Social Memory Lite

Social Memory Lite beobachtet ausschließlich öffentliche RSS-Feeds und die offizielle Reddit Data API. Das Modul speichert normalisierte Beiträge append-sicher, ordnet ausschließlich BTC, ETH und XRP zu und misst danach deskriptive Marktreaktionen. Es erzeugt keine Trading-Signale und ist nicht mit Shitzo, dem Decision Core, Pandorick, Brokern oder Nachrichtendiensten verbunden.

## Datenfluss

`RSS / Reddit -> Read-only Adapter -> Normalizer / Classifier -> SQLite Event Store -> Reaction Queue -> Coinbase Public Candles -> Historical Matches -> Hypothesis Candidates -> GET-only API -> Control Center`

Die Reaktions-Queue enthält je relevantem Ereignis und Asset genau fünf idempotente Jobs: `T0`, `+5m`, `+30m`, `+2h` und `+24h`. Jobs im Zustand `PROCESSING` werden nach einem Neustart nach `FAILED_RETRYABLE` zurückgeführt. Nach drei Fehlversuchen endet ein Job in `FAILED_FINAL`.

## Quellen

- RSS: CoinDesk, Cointelegraph, SEC und Federal Reserve.
- Binance und Kraken bleiben sichtbar als `UNAVAILABLE_NO_OFFICIAL_FEED`, solange kein verifizierter offizieller allgemeiner RSS-Feed vorliegt. Es gibt keinen Scraping-Fallback.
- Reddit: `r/Bitcoin`, `r/CryptoCurrency`, `r/Ethereum`, `r/XRP` über OAuth Client Credentials und ausschließlich lesende Listing-Aufrufe.
- Marktreaktionen: öffentliche Coinbase-Minutenkerzen, ausschließlich zur historischen Messung.
- X/Twitter ist deaktiviert und nicht Teil der aktiven Komposition.

## Aktivierung

Das Modul ist fail-closed und standardmäßig ausgeschaltet:

```text
STIMPY_SOCIAL_MEMORY_LITE_ENABLED=1
STIMPY_RSS_ENABLED=1
STIMPY_REDDIT_ENABLED=0
STIMPY_SOCIAL_POLL_SECONDS=300
```

Für Reddit zusätzlich:

```text
STIMPY_REDDIT_ENABLED=1
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
REDDIT_USER_AGENT=StimpyBrain-SocialMemoryLite/1.0
```

Geheimnisse gehören nur in lokale Umgebungsvariablen und niemals ins Repository. Ohne Reddit-Zugangsdaten bleibt Reddit sichtbar deaktiviert; RSS kann unabhängig weiterlaufen.

## Read-only API

Alle Endpunkte akzeptieren nur GET:

- `/api/stimpy/social-lite/status`
- `/api/stimpy/social-lite/feed`
- `/api/stimpy/social-lite/interesting`
- `/api/stimpy/social-lite/reactions`
- `/api/stimpy/social-lite/history`
- `/api/stimpy/social-lite/queue`
- `/api/stimpy/social-lite/sources`
- `/api/stimpy/social-lite/hypotheses`

POST, PUT, PATCH und DELETE liefern HTTP 405. Hypothesen sind ausschließlich prüfbare Kandidaten aus historischen Zusammenhängen; sie werden nicht automatisch zu Trading-Entscheidungen hochgestuft.

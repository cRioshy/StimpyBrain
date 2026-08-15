"""Public, credential-free, GET-only Coinbase Exchange ticker adapter."""
from __future__ import annotations

import hashlib
import json
import urllib.request
from datetime import UTC, datetime

from .shitzo.market_feed import MarketFeedError
from .shitzo.models import MarketTick


class CoinbasePublicTickerFeed:
    source_name = "coinbase-exchange-public-ticker"

    def __init__(self, timeout_seconds: float = 5.0):
        self.timeout_seconds = float(timeout_seconds)

    def read_latest(self, symbol: str) -> MarketTick:
        normalized = symbol.strip().upper()
        url = f"https://api.exchange.coinbase.com/products/{normalized}/ticker"
        request = urllib.request.Request(url, headers={"User-Agent": "StimpyBrain-paper-research/1.0"}, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.load(response)
            now = datetime.now(UTC)
            price = float(payload["price"])
            volume = float(payload["volume"]) if payload.get("volume") is not None else None
            event_id = hashlib.sha256(f"{self.source_name}|{normalized}|{now.isoformat()}|{price}".encode()).hexdigest()
            return MarketTick(normalized, price, now, self.source_name, event_id, volume)
        except Exception as error:
            raise MarketFeedError(f"public ticker failed for {normalized}: {error}") from error

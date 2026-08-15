"""Bounded chronological tick window producing frozen feature snapshots."""
from __future__ import annotations

import hashlib
from collections import deque
from math import sqrt
from .models import FeatureSnapshot, MarketTick


class PriceWindow:
    def __init__(self, symbol: str, *, short_period: int = 5, long_period: int = 20):
        if short_period < 2 or long_period <= short_period:
            raise ValueError("periods require 2 <= short < long")
        self.symbol = symbol.strip().upper()
        self.short_period = short_period
        self.long_period = long_period
        self._ticks: deque[MarketTick] = deque(maxlen=long_period)
        self._ids: set[str] = set()

    @property
    def ready(self) -> bool:
        return len(self._ticks) == self.long_period

    def add(self, tick: MarketTick) -> bool:
        if tick.symbol != self.symbol:
            raise ValueError("tick symbol does not match window")
        if self._ticks and tick.timestamp <= self._ticks[-1].timestamp:
            raise ValueError("ticks must be strictly chronological")
        if tick.source_event_id in self._ids:
            return False
        if len(self._ticks) == self.long_period:
            self._ids.remove(self._ticks[0].source_event_id)
        self._ticks.append(tick)
        self._ids.add(tick.source_event_id)
        return True

    def snapshot(self) -> FeatureSnapshot:
        if not self.ready:
            raise RuntimeError("insufficient data for a frozen snapshot")
        ticks = tuple(self._ticks)
        prices = tuple(t.price for t in ticks)
        short_ma = sum(prices[-self.short_period:]) / self.short_period
        long_ma = sum(prices) / len(prices)
        momentum = prices[-1] / prices[0] - 1.0
        returns = tuple(prices[i] / prices[i - 1] - 1.0 for i in range(1, len(prices)))
        mean = sum(returns) / len(returns)
        volatility = sqrt(sum((r - mean) ** 2 for r in returns) / len(returns))
        ids = tuple(t.source_event_id for t in ticks)
        identity = "|".join((self.symbol, str(self.short_period), str(self.long_period), *ids))
        return FeatureSnapshot(
            snapshot_id=hashlib.sha256(identity.encode()).hexdigest(), symbol=self.symbol,
            timestamp=ticks[-1].timestamp, window_started_at=ticks[0].timestamp,
            window_ended_at=ticks[-1].timestamp, price=prices[-1], short_ma=short_ma,
            long_ma=long_ma, momentum=momentum, volatility=volatility,
            sample_count=len(ticks), source=ticks[-1].source, source_data_ids=ids)

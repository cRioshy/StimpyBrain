"""Strict immutable records for the Shitzo paper-research foundation."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from math import isfinite

SUPPORTED_SYMBOLS = frozenset({"BTC-USD", "ETH-USD", "XRP-USD"})


def _timestamp(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(UTC)


def _finite(name: str, value: float, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be numeric")
    result = float(value)
    if not isfinite(result) or (positive and result <= 0):
        raise ValueError(f"{name} must be finite" + (" and positive" if positive else ""))
    return result


def _symbol(value: str) -> str:
    normalized = str(value).strip().upper()
    if normalized not in SUPPORTED_SYMBOLS:
        raise ValueError("unsupported Shitzo symbol")
    return normalized


class Direction(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"
    WAIT = "WAIT"


@dataclass(frozen=True)
class MarketTick:
    symbol: str
    price: float
    timestamp: datetime
    source: str
    source_event_id: str
    volume: float | None = None
    schema_version: int = 1

    def __post_init__(self):
        object.__setattr__(self, "symbol", _symbol(self.symbol))
        object.__setattr__(self, "price", _finite("price", self.price, positive=True))
        object.__setattr__(self, "timestamp", _timestamp(self.timestamp))
        if not self.source.strip() or not self.source_event_id.strip():
            raise ValueError("source and source_event_id are required")
        if self.volume is not None:
            volume = _finite("volume", self.volume)
            if volume < 0:
                raise ValueError("volume must not be negative")
            object.__setattr__(self, "volume", volume)
        if self.schema_version != 1:
            raise ValueError("unsupported MarketTick schema")


@dataclass(frozen=True)
class TraderDecision:
    decision_id: str
    trader_id: str
    symbol: str
    direction: Direction
    confidence: float
    reason: str
    timestamp: datetime
    feature_snapshot_id: str
    strategy_version: str
    schema_version: int = 1

    def __post_init__(self):
        for name in ("decision_id", "trader_id", "reason", "feature_snapshot_id", "strategy_version"):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"{name} is required")
        object.__setattr__(self, "symbol", _symbol(self.symbol))
        object.__setattr__(self, "direction", Direction(self.direction))
        confidence = _finite("confidence", self.confidence)
        if not 0 <= confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        object.__setattr__(self, "confidence", confidence)
        object.__setattr__(self, "timestamp", _timestamp(self.timestamp))
        if self.schema_version != 1:
            raise ValueError("unsupported TraderDecision schema")


@dataclass(frozen=True)
class FeatureSnapshot:
    snapshot_id: str
    symbol: str
    timestamp: datetime
    window_started_at: datetime
    window_ended_at: datetime
    price: float
    short_ma: float
    long_ma: float
    momentum: float
    volatility: float
    sample_count: int
    source: str
    source_data_ids: tuple[str, ...]
    available_timeframes: tuple[str, ...] = ()
    market_regime: str | None = None
    data_quality: str = "VALID"
    schema_version: int = 1

    def __post_init__(self):
        if not self.snapshot_id.strip() or not self.source.strip():
            raise ValueError("snapshot_id and source are required")
        object.__setattr__(self, "symbol", _symbol(self.symbol))
        for name in ("timestamp", "window_started_at", "window_ended_at"):
            object.__setattr__(self, name, _timestamp(getattr(self, name)))
        if self.window_started_at > self.window_ended_at or self.timestamp != self.window_ended_at:
            raise ValueError("snapshot time bounds are inconsistent")
        for name in ("price", "short_ma", "long_ma"):
            object.__setattr__(self, name, _finite(name, getattr(self, name), positive=True))
        for name in ("momentum", "volatility"):
            object.__setattr__(self, name, _finite(name, getattr(self, name)))
        if self.volatility < 0 or self.sample_count < 2:
            raise ValueError("snapshot requires at least two samples and non-negative volatility")
        if len(self.source_data_ids) != self.sample_count or len(set(self.source_data_ids)) != self.sample_count:
            raise ValueError("source_data_ids must uniquely identify every sample")
        if self.data_quality != "VALID" or self.schema_version != 1:
            raise ValueError("unsupported snapshot quality or schema")

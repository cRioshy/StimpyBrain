"""Capability-minimal read-only market-data contract."""
from __future__ import annotations

from typing import Protocol, runtime_checkable
from .models import MarketTick


class MarketFeedError(RuntimeError):
    """Bounded feed failure; callers must fail closed."""


@runtime_checkable
class MarketDataFeed(Protocol):
    @property
    def source_name(self) -> str: ...

    def read_latest(self, symbol: str) -> MarketTick: ...


def validate_read_only_feed(feed: object) -> None:
    """Reject objects exposing obvious write/trading capabilities."""
    forbidden = ("create_order", "place_order", "cancel_order", "transfer", "withdraw")
    exposed = [name for name in forbidden if callable(getattr(feed, name, None))]
    if exposed:
        raise TypeError(f"market feed exposes forbidden capabilities: {', '.join(exposed)}")
    if not isinstance(feed, MarketDataFeed):
        raise TypeError("feed does not satisfy the read-only MarketDataFeed contract")

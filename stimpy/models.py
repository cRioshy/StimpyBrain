"""Domain models for passive StimpyBrain observations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from math import isfinite
from typing import Any


def utc_now() -> datetime:
    return datetime.now(UTC)


def parse_timestamp(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must contain a timezone")
    return parsed.astimezone(UTC)


def finite_number(
    value: Any,
    name: str,
    *,
    minimum: float = 0.0,
    maximum: float = 1e18,
    allow_zero: bool = False,
) -> float:
    number = float(value)
    lower_ok = number >= minimum if allow_zero else number > minimum
    if not isfinite(number) or not lower_ok or number > maximum:
        comparator = ">=" if allow_zero else ">"
        raise ValueError(f"{name} must be finite, {comparator} {minimum}, and <= {maximum}")
    return number


@dataclass(frozen=True)
class Observation:
    event_id: str
    correlation_id: str
    topic: str
    source: str
    market: str
    symbol: str
    observed_at: datetime
    payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("event_id", "correlation_id", "topic", "source", "market", "symbol"):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"{name} must not be empty")
        if self.observed_at.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware")
        if not isinstance(self.payload, dict):
            raise TypeError("payload must be a dictionary")


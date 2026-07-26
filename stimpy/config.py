"""Safe phase-1 configuration for the standalone StimpyBrain project."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


@dataclass(frozen=True)
class StimpyConfig:
    """Configuration that deliberately exposes no broker or outbound channel."""

    database_path: Path = PROJECT_ROOT / "runtime" / "stimpy.sqlite3"
    mode: str = "observe"
    max_audit_bytes: int = 65_536
    audit_preview_chars: int = 512
    max_event_age_seconds: float = 300.0
    max_future_skew_seconds: float = 5.0
    observation_topics: tuple[str, ...] = (
        "CRYPTO_ANALYSIS_FINISHED",
        "STOCK_ANALYSIS_FINISHED",
        "COMMODITY_ANALYSIS_FINISHED",
        "BRAIN_DECISION_RECEIVED",
        "DECISION_CREATED",
        "SIGNAL_CREATED",
        "TRADE_OUTCOME_RECORDED",
    )

    @classmethod
    def from_env(cls) -> "StimpyConfig":
        path = Path(os.getenv("STIMPY_DATABASE_PATH", str(cls.database_path)))
        return cls(
            database_path=path,
            mode="observe",
            max_audit_bytes=max(_env_int("STIMPY_MAX_AUDIT_BYTES", 65_536), 1_024),
            audit_preview_chars=max(_env_int("STIMPY_AUDIT_PREVIEW_CHARS", 512), 64),
            max_event_age_seconds=max(_env_float("STIMPY_MAX_EVENT_AGE_SECONDS", 300.0), 1.0),
            max_future_skew_seconds=max(_env_float("STIMPY_MAX_FUTURE_SKEW_SECONDS", 5.0), 0.0),
        )

    def validate(self) -> None:
        if self.mode != "observe":
            raise ValueError("StimpyBrain phase 1 permits observe mode only")


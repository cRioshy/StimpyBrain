"""Deterministic, look-ahead-free market-regime classification."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from math import isfinite

from .models import FeatureSnapshot


@dataclass(frozen=True)
class RegimeRules:
    trend_spread_threshold: float = .0002
    low_volatility_threshold: float = .0001
    high_volatility_threshold: float = .0005
    version: str = "shitzo-regime-v1"

    def __post_init__(self):
        values=(self.trend_spread_threshold,self.low_volatility_threshold,self.high_volatility_threshold)
        if not all(isfinite(float(x)) and x>0 for x in values): raise ValueError("regime thresholds must be positive and finite")
        if self.low_volatility_threshold>=self.high_volatility_threshold: raise ValueError("volatility thresholds must be ordered")
        if not self.version.strip(): raise ValueError("classifier version is required")


@dataclass(frozen=True)
class RegimeLabel:
    snapshot_id: str
    run_id: str
    symbol: str
    trend_regime: str
    volatility_regime: str
    combined_regime: str
    classifier_version: str
    reasons: tuple[str,...]
    classified_at: datetime
    source_type: str = "LIVE"
    schema_version: int = 1
    label_id: str = ""

    def __post_init__(self):
        allowed_trend={"UP_TREND","DOWN_TREND","RANGE","INSUFFICIENT_DATA"};allowed_vol={"LOW_VOLATILITY","NORMAL_VOLATILITY","HIGH_VOLATILITY","INSUFFICIENT_DATA"}
        if self.trend_regime not in allowed_trend or self.volatility_regime not in allowed_vol: raise ValueError("unsupported regime")
        if self.source_type not in {"LIVE","HISTORICAL_BACKFILL"}: raise ValueError("unsupported regime source")
        if self.classified_at.tzinfo is None: raise ValueError("classified_at must be timezone-aware")
        if not self.label_id: object.__setattr__(self,"label_id","regime-"+hashlib.sha256(f"{self.snapshot_id}|{self.classifier_version}".encode()).hexdigest())


class MarketRegimeClassifier:
    def __init__(self,rules=None): self.rules=rules or RegimeRules()

    def classify(self,snapshot:FeatureSnapshot,run_id:str,source_type="LIVE",classified_at=None):
        if snapshot.sample_count<2 or snapshot.data_quality!="VALID":
            trend=vol="INSUFFICIENT_DATA";reasons=("insufficient or invalid frozen snapshot",)
        else:
            spread=(snapshot.short_ma-snapshot.long_ma)/snapshot.long_ma
            if spread>=self.rules.trend_spread_threshold and snapshot.momentum>0: trend="UP_TREND"
            elif spread<=-self.rules.trend_spread_threshold and snapshot.momentum<0: trend="DOWN_TREND"
            else: trend="RANGE"
            if snapshot.volatility<=self.rules.low_volatility_threshold: vol="LOW_VOLATILITY"
            elif snapshot.volatility>=self.rules.high_volatility_threshold: vol="HIGH_VOLATILITY"
            else: vol="NORMAL_VOLATILITY"
            reasons=(f"ma_spread={spread:.8f}; threshold={self.rules.trend_spread_threshold:.8f}",f"momentum={snapshot.momentum:.8f}",f"volatility={snapshot.volatility:.8f}; low={self.rules.low_volatility_threshold:.8f}; high={self.rules.high_volatility_threshold:.8f}")
        combined=f"{trend}_{vol}" if "INSUFFICIENT_DATA" not in {trend,vol} else "INSUFFICIENT_DATA"
        return RegimeLabel(snapshot.snapshot_id,run_id,snapshot.symbol,trend,vol,combined,self.rules.version,reasons,(classified_at or datetime.now(UTC)).astimezone(UTC),source_type)

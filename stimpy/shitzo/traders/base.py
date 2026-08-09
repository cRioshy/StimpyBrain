"""Capability-free base contract for deterministic research traders."""
from __future__ import annotations
import hashlib
from abc import ABC,abstractmethod
from dataclasses import dataclass
from math import isfinite
from ..models import Direction,FeatureSnapshot,TraderDecision


class InsufficientDataError(ValueError): pass


@dataclass(frozen=True)
class TraderRules:
    threshold: float
    max_confidence: float=.75
    strategy_version: str="v1"
    def __post_init__(self):
        if not isfinite(float(self.threshold)) or self.threshold<=0: raise ValueError("threshold must be finite and positive")
        if not isfinite(float(self.max_confidence)) or not .55<=self.max_confidence<=.75: raise ValueError("max confidence must be between .55 and .75")
        if not self.strategy_version.strip(): raise ValueError("strategy version is required")


class SnapshotTrader(ABC):
    trader_id: str
    def __init__(self,rules:TraderRules): self.rules=rules
    def decide(self,snapshot:FeatureSnapshot|None)->TraderDecision:
        if snapshot is None: raise InsufficientDataError("a frozen FeatureSnapshot is required")
        direction,strength,reason=self._evaluate(snapshot)
        confidence=0.0 if direction is Direction.WAIT else min(self.rules.max_confidence,.55+.20*min(1.0,strength/(self.rules.threshold*5)))
        identity=f"{self.trader_id}|{self.rules.strategy_version}|{snapshot.snapshot_id}|{direction.value}|{confidence:.12g}"
        return TraderDecision(hashlib.sha256(identity.encode()).hexdigest(),self.trader_id,snapshot.symbol,direction,confidence,reason,snapshot.timestamp,snapshot.snapshot_id,self.rules.strategy_version)
    @abstractmethod
    def _evaluate(self,snapshot:FeatureSnapshot)->tuple[Direction,float,str]: ...

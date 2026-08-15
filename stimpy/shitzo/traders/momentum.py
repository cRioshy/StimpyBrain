from __future__ import annotations
from .base import SnapshotTrader,TraderRules
from ..models import Direction,FeatureSnapshot


class MomentumTrader(SnapshotTrader):
    trader_id="shitzo-momentum"
    def __init__(self,threshold=.0015,max_confidence=.75,strategy_version="momentum-v1-half-threshold"): super().__init__(TraderRules(threshold,max_confidence,strategy_version))
    def _evaluate(self,snapshot:FeatureSnapshot):
        strength=abs(snapshot.momentum)
        if strength<self.rules.threshold: direction=Direction.WAIT
        else: direction=Direction.LONG if snapshot.momentum>0 else Direction.SHORT
        return direction,strength,f"window momentum={snapshot.momentum:.6f}; threshold={self.rules.threshold:.6f}; deterministic momentum experiment"

from __future__ import annotations
from .base import SnapshotTrader,TraderRules
from ..models import Direction,FeatureSnapshot


class TrendTrader(SnapshotTrader):
    trader_id="shitzo-trend"
    def __init__(self,threshold=.0005,max_confidence=.75,strategy_version="trend-v1-half-threshold"): super().__init__(TraderRules(threshold,max_confidence,strategy_version))
    def _evaluate(self,snapshot:FeatureSnapshot):
        spread=(snapshot.short_ma-snapshot.long_ma)/snapshot.long_ma; strength=abs(spread)
        if strength<self.rules.threshold: direction=Direction.WAIT
        else: direction=Direction.LONG if spread>0 else Direction.SHORT
        return direction,strength,f"short/long MA spread={spread:.6f}; threshold={self.rules.threshold:.6f}; deterministic trend experiment"

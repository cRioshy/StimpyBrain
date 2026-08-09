from __future__ import annotations
from .base import SnapshotTrader,TraderRules
from ..models import Direction,FeatureSnapshot


class ContrarianTrader(SnapshotTrader):
    trader_id="shitzo-contrarian"
    def __init__(self,threshold=.005,max_confidence=.75,strategy_version="contrarian-v1"): super().__init__(TraderRules(threshold,max_confidence,strategy_version))
    def _evaluate(self,snapshot:FeatureSnapshot):
        deviation=(snapshot.price-snapshot.long_ma)/snapshot.long_ma; strength=abs(deviation)
        if strength<self.rules.threshold: direction=Direction.WAIT
        else: direction=Direction.SHORT if deviation>0 else Direction.LONG
        return direction,strength,f"price/long-MA deviation={deviation:.6f}; threshold={self.rules.threshold:.6f}; deterministic mean-reversion experiment"

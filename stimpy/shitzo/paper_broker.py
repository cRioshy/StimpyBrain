"""Purely virtual broker: deterministic arithmetic, zero network capabilities."""
from __future__ import annotations
import hashlib
from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from .models import Direction, ExitReason, FeatureSnapshot, PaperPosition, ResultType, TraderDecision


@dataclass(frozen=True)
class PaperBrokerRules:
    risk_per_trade: float=.005
    min_confidence: float=.55
    stop_distance_pct: float=.005
    take_profit_distance_pct: float=.010
    def __post_init__(self):
        for name in ("risk_per_trade","min_confidence","stop_distance_pct","take_profit_distance_pct"):
            value=float(getattr(self,name))
            if not isfinite(value) or value<=0 or value>1: raise ValueError(f"invalid {name}")


class PaperBroker:
    def __init__(self,repository,rules=None): self.repository=repository; self.rules=rules or PaperBrokerRules()
    def consider(self,run_id,decision:TraderDecision,snapshot:FeatureSnapshot):
        if decision.feature_snapshot_id!=snapshot.snapshot_id or decision.symbol!=snapshot.symbol: raise ValueError("decision/snapshot mismatch")
        self.repository.save_snapshot_and_decision(run_id,snapshot,decision)
        if decision.direction is Direction.WAIT or decision.confidence<self.rules.min_confidence: return None
        account=self.repository.get_account(run_id,decision.trader_id)
        if not account: raise KeyError("virtual account is required")
        entry=snapshot.price; stop=entry*(1-self.rules.stop_distance_pct if decision.direction is Direction.LONG else 1+self.rules.stop_distance_pct); take=entry*(1+self.rules.take_profit_distance_pct if decision.direction is Direction.LONG else 1-self.rules.take_profit_distance_pct)
        risk_usd=account.balance*self.rules.risk_per_trade; available=self.repository.available_notional(run_id,decision.trader_id); quantity=min(risk_usd/abs(entry-stop),available/entry)
        if quantity<=0: return None
        identity=f"{run_id}|{decision.decision_id}|{entry:.12g}|{quantity:.12g}"
        position=PaperPosition(hashlib.sha256(identity.encode()).hexdigest(),run_id,decision.trader_id,decision.symbol,decision.direction,entry,quantity,stop,take,decision.timestamp,decision.decision_id)
        return self.repository.open_position(position)
    def update_price(self,position:PaperPosition,price:float,timestamp:datetime):
        price=float(price)
        if not isfinite(price) or price<=0: raise ValueError("price must be finite and positive")
        if timestamp.tzinfo is None or timestamp<position.opened_at: raise ValueError("invalid close timestamp")
        reason=None
        if position.side is Direction.LONG:
            if price<=position.stop_loss: reason=ExitReason.STOP_LOSS
            elif price>=position.take_profit: reason=ExitReason.TAKE_PROFIT
            pnl=(price-position.entry_price)*position.quantity
        else:
            if price>=position.stop_loss: reason=ExitReason.STOP_LOSS
            elif price<=position.take_profit: reason=ExitReason.TAKE_PROFIT
            pnl=(position.entry_price-price)*position.quantity
        if reason is None: return None
        result=ResultType.WIN if pnl>0 else ResultType.LOSS if pnl<0 else ResultType.NEUTRAL
        context={"entry_price":position.entry_price,"stop_loss":position.stop_loss,"take_profit":position.take_profit,"decision_id":position.decision_id}
        return self.repository.close_position(position.position_id,price,timestamp,pnl,result.value,reason.value,context)
    def manual_test_close(self,position:PaperPosition,price:float,timestamp:datetime):
        price=float(price)
        if not isfinite(price) or price<=0 or timestamp.tzinfo is None or timestamp<position.opened_at: raise ValueError("invalid manual close")
        pnl=(price-position.entry_price)*position.quantity*(1 if position.side is Direction.LONG else -1)
        result=ResultType.WIN if pnl>0 else ResultType.LOSS if pnl<0 else ResultType.NEUTRAL
        return self.repository.close_position(position.position_id,price,timestamp,pnl,result.value,ExitReason.MANUAL_TEST_CLOSE.value,{"decision_id":position.decision_id,"manual_test":True})

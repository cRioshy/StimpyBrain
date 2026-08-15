"""Explicit bounded orchestration; no scheduler, thread or network client."""
from __future__ import annotations
import hashlib
from datetime import UTC,datetime
from .models import MarketTick
from .paper_broker import PaperBroker,PaperBrokerRules
from .price_window import PriceWindow
from .traders import ContrarianTrader,MomentumTrader,TrendTrader


class ShitzoDisabledError(RuntimeError): pass


class ShitzoLab:
    def __init__(self,repository,config,traders=None):
        self.repository=repository;self.config=config;self.traders=tuple(traders or (
            TrendTrader(config.shitzo_trend_threshold,strategy_version=f"trend-v1-threshold-{config.shitzo_trend_threshold:.6f}"),
            MomentumTrader(config.shitzo_momentum_threshold,strategy_version=f"momentum-v1-threshold-{config.shitzo_momentum_threshold:.6f}"),
            ContrarianTrader(config.shitzo_contrarian_threshold,strategy_version=f"contrarian-v1-threshold-{config.shitzo_contrarian_threshold:.6f}")))
        rules=PaperBrokerRules(config.shitzo_risk_per_trade,config.shitzo_min_confidence,config.shitzo_stop_distance_pct,config.shitzo_take_profit_distance_pct,config.shitzo_max_holding_seconds)
        self.broker=PaperBroker(repository,rules);self._run_id=None;self._windows={}
    @property
    def active(self): return self._run_id is not None
    def start(self,run_id=None,now=None):
        if not self.config.shitzo_enabled: raise ShitzoDisabledError("SHITZO_ENABLED is false")
        if self.active: return self._run_id
        now=(now or datetime.now(UTC)).astimezone(UTC);configuration={"symbols":self.config.shitzo_symbols,"starting_balance":self.config.shitzo_starting_balance_usd,"risk_per_trade":self.config.shitzo_risk_per_trade,"min_confidence":self.config.shitzo_min_confidence,"stop_distance_pct":self.config.shitzo_stop_distance_pct,"take_profit_distance_pct":self.config.shitzo_take_profit_distance_pct,"max_holding_seconds":self.config.shitzo_max_holding_seconds,"thresholds":{"trend":self.config.shitzo_trend_threshold,"momentum":self.config.shitzo_momentum_threshold,"contrarian":self.config.shitzo_contrarian_threshold},"automatic":self.config.shitzo_autorun,"network_provider":"coinbase-exchange-public-ticker" if self.config.shitzo_autorun else None}
        run_id=run_id or hashlib.sha256(f"shitzo|{now.isoformat()}|{configuration}".encode()).hexdigest()
        self.repository.create_run(run_id,configuration);self.repository.start_run(run_id,now)
        for trader in self.traders: self.repository.create_account(run_id,trader.trader_id,self.config.shitzo_starting_balance_usd,now)
        self._windows={symbol:PriceWindow(symbol) for symbol in self.config.shitzo_symbols};self._run_id=run_id;return run_id
    def process_tick(self,tick:MarketTick,received_at=None):
        if not self.active: raise RuntimeError("ShitzoLab is not explicitly started")
        if tick.symbol not in self._windows: raise ValueError("symbol is outside this lab run")
        received_at=(received_at or datetime.now(UTC)).astimezone(UTC);self.repository.save_tick(self._run_id,tick,received_at)
        closed=[]
        for trader in self.traders:
            position=self.repository.get_open_position(self._run_id,trader.trader_id,tick.symbol)
            if position:
                trade=self.broker.update_price(position,tick.price,tick.timestamp)
                if trade: closed.append(trade)
        window=self._windows[tick.symbol]
        if not window.add(tick) or not window.ready: return {"snapshot":None,"decisions":[],"opened":[],"closed":closed}
        snapshot=window.snapshot();decisions=[];opened=[]
        for trader in self.traders:
            decision=trader.decide(snapshot);decisions.append(decision)
            position=self.broker.consider(self._run_id,decision,snapshot)
            if position: opened.append(position)
        return {"snapshot":snapshot,"decisions":decisions,"opened":opened,"closed":closed}
    def stop(self,now=None):
        if not self.active: return False
        self.repository.stop_run(self._run_id,(now or datetime.now(UTC)).astimezone(UTC));self._run_id=None;self._windows={};return True
    def status(self):
        run=self.repository.get_run(self._run_id) if self.active else self.repository.latest_run()
        return {"enabled":self.config.shitzo_enabled,"active":self.active,"automatic":False,"live_provider":False,"real_orders":False,"run":run}

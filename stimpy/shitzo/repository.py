"""Transactional SQLite repository for virtual Shitzo research state."""
from __future__ import annotations
import json, sqlite3
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from .models import FeatureSnapshot, PaperPosition, PositionStatus, TraderAccount, TraderDecision


class ShitzoRepository:
    def __init__(self, database_path):
        self._db=sqlite3.connect(Path(database_path),check_same_thread=False); self._db.row_factory=sqlite3.Row; self._lock=RLock()
        self._db.execute("PRAGMA foreign_keys=ON")
        required={"shitzo_lab_runs","shitzo_accounts","shitzo_feature_snapshots","shitzo_decisions","shitzo_positions","shitzo_trades"}
        found={r[0] for r in self._db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'shitzo_%'")}
        if not required.issubset(found): self._db.close(); raise RuntimeError("Shitzo schema v12 is required")
    def close(self): self._db.close()
    def create_run(self,run_id,configuration):
        now=datetime.now(UTC).isoformat()
        with self._lock,self._db: self._db.execute("INSERT OR IGNORE INTO shitzo_lab_runs VALUES(?,?,?,?,?,?,?)",(run_id,"CREATED",json.dumps(configuration,sort_keys=True),None,None,now,1))
        return run_id
    def create_account(self,run_id,trader_id,starting_balance,now):
        with self._lock,self._db:
            self._db.execute("INSERT OR IGNORE INTO shitzo_accounts(run_id,trader_id,starting_balance,balance,realized_pnl,trades,wins,losses,max_drawdown,updated_at,schema_version,peak_balance) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(run_id,trader_id,starting_balance,starting_balance,0.0,0,0,0,0.0,now.isoformat(),1,starting_balance))
        return self.get_account(run_id,trader_id)
    def save_snapshot_and_decision(self,run_id,snapshot:FeatureSnapshot,decision:TraderDecision):
        features={"price":snapshot.price,"short_ma":snapshot.short_ma,"long_ma":snapshot.long_ma,"momentum":snapshot.momentum,"volatility":snapshot.volatility,"sample_count":snapshot.sample_count,"source":snapshot.source,"available_timeframes":snapshot.available_timeframes,"market_regime":snapshot.market_regime,"data_quality":snapshot.data_quality}
        with self._lock,self._db:
            self._db.execute("INSERT OR IGNORE INTO shitzo_feature_snapshots VALUES(?,?,?,?,?,?,?,?,?)",(snapshot.snapshot_id,run_id,snapshot.symbol,snapshot.timestamp.isoformat(),snapshot.window_started_at.isoformat(),snapshot.window_ended_at.isoformat(),json.dumps(features,sort_keys=True),json.dumps(snapshot.source_data_ids),snapshot.schema_version))
            self._db.execute("INSERT OR IGNORE INTO shitzo_decisions VALUES(?,?,?,?,?,?,?,?,?,?,?)",(decision.decision_id,run_id,decision.trader_id,decision.symbol,decision.direction.value,decision.confidence,decision.reason,decision.timestamp.isoformat(),decision.feature_snapshot_id,decision.strategy_version,decision.schema_version))
    def open_position(self,position:PaperPosition):
        with self._lock,self._db:
            existing=self._db.execute("SELECT position_id FROM shitzo_positions WHERE run_id=? AND trader_id=? AND symbol=? AND status='OPEN'",(position.run_id,position.trader_id,position.symbol)).fetchone()
            if existing: return None
            account=self._db.execute("SELECT balance FROM shitzo_accounts WHERE run_id=? AND trader_id=?",(position.run_id,position.trader_id)).fetchone()
            committed=float(self._db.execute("SELECT COALESCE(SUM(entry_price*quantity),0) FROM shitzo_positions WHERE run_id=? AND trader_id=? AND status='OPEN'",(position.run_id,position.trader_id)).fetchone()[0])
            if not account or committed+position.entry_price*position.quantity>float(account["balance"])+1e-9: return None
            self._db.execute("INSERT INTO shitzo_positions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(position.position_id,position.run_id,position.trader_id,position.symbol,position.side.value,position.entry_price,position.quantity,position.stop_loss,position.take_profit,position.opened_at.isoformat(),None,None,None,position.status.value,position.decision_id,position.schema_version))
        return position
    def available_notional(self,run_id,trader_id):
        account=self._db.execute("SELECT balance FROM shitzo_accounts WHERE run_id=? AND trader_id=?",(run_id,trader_id)).fetchone()
        if not account: raise KeyError("virtual account is required")
        committed=float(self._db.execute("SELECT COALESCE(SUM(entry_price*quantity),0) FROM shitzo_positions WHERE run_id=? AND trader_id=? AND status='OPEN'",(run_id,trader_id)).fetchone()[0])
        return max(0.0,float(account["balance"])-committed)
    def close_position(self,position_id,exit_price,closed_at,pnl,result_type,exit_reason,frozen_context):
        trade_id=f"trade-{position_id}"
        with self._lock,self._db:
            row=self._db.execute("SELECT * FROM shitzo_positions WHERE position_id=?",(position_id,)).fetchone()
            if not row: raise KeyError(position_id)
            if row["status"]!="OPEN": return self.get_trade(position_id)
            self._db.execute("UPDATE shitzo_positions SET closed_at=?,exit_price=?,pnl_usd=?,status='CLOSED' WHERE position_id=? AND status='OPEN'",(closed_at.isoformat(),exit_price,pnl,position_id))
            self._db.execute("INSERT INTO shitzo_trades VALUES(?,?,?,?,?,?,?,?,?,?)",(trade_id,position_id,row["run_id"],result_type,exit_reason,exit_price,pnl,closed_at.isoformat(),json.dumps(frozen_context,sort_keys=True),1))
            account=self._db.execute("SELECT * FROM shitzo_accounts WHERE run_id=? AND trader_id=?",(row["run_id"],row["trader_id"])).fetchone()
            balance=float(account["balance"])+pnl; realized=float(account["realized_pnl"])+pnl; trades=int(account["trades"])+1
            wins=int(account["wins"])+(result_type=="WIN"); losses=int(account["losses"])+(result_type=="LOSS"); peak=max(float(account["peak_balance"]),balance); drawdown=max(float(account["max_drawdown"]),max(0.0,peak-balance))
            self._db.execute("UPDATE shitzo_accounts SET balance=?,realized_pnl=?,trades=?,wins=?,losses=?,max_drawdown=?,updated_at=?,peak_balance=? WHERE run_id=? AND trader_id=?",(balance,realized,trades,wins,losses,drawdown,closed_at.isoformat(),peak,row["run_id"],row["trader_id"]))
        return self.get_trade(position_id)
    def get_account(self,run_id,trader_id):
        r=self._db.execute("SELECT * FROM shitzo_accounts WHERE run_id=? AND trader_id=?",(run_id,trader_id)).fetchone()
        if not r: return None
        return TraderAccount(r["run_id"],r["trader_id"],r["starting_balance"],r["balance"],r["realized_pnl"],r["trades"],r["wins"],r["losses"],r["max_drawdown"],datetime.fromisoformat(r["updated_at"]),r["schema_version"])
    def get_open_position(self,run_id,trader_id,symbol):
        r=self._db.execute("SELECT * FROM shitzo_positions WHERE run_id=? AND trader_id=? AND symbol=? AND status='OPEN'",(run_id,trader_id,symbol)).fetchone()
        return self._position(r) if r else None
    def get_trade(self,position_id):
        r=self._db.execute("SELECT * FROM shitzo_trades WHERE position_id=?",(position_id,)).fetchone(); return dict(r) if r else None
    @staticmethod
    def _position(r):
        return PaperPosition(r["position_id"],r["run_id"],r["trader_id"],r["symbol"],r["side"],r["entry_price"],r["quantity"],r["stop_loss"],r["take_profit"],datetime.fromisoformat(r["opened_at"]),r["decision_id"],PositionStatus(r["status"]),datetime.fromisoformat(r["closed_at"]) if r["closed_at"] else None,r["exit_price"],r["pnl_usd"],r["schema_version"])

"""Deterministic, chronological, local-only OHLCV replay foundation."""
from __future__ import annotations
import csv,hashlib,json
from datetime import UTC,datetime
from math import isfinite,sqrt
from pathlib import Path
from .models import parse_timestamp

RULES=("trend_momentum","overextended_momentum","breakout","false_breakout","retest","volatility","volume","multi_timeframe","market_regime","time_dependence")

class OfflineReplayService:
    def __init__(self,store,clock=None): self.store=store; self.clock=clock or (lambda:datetime.now(UTC))
    def run_csv(self,path,symbol="BTCUSD",timeframe="15m",horizon=4,threshold=.001):
        path=Path(path); raw=path.read_bytes(); rows=self._load(path); horizon=max(1,min(int(horizon),96)); threshold=float(threshold)
        if not isfinite(threshold) or not 0<threshold<=.10: raise ValueError("threshold must be finite and between 0 and .10")
        config={"horizon":horizon,"threshold":threshold,"split":[.6,.2,.2],"rules":RULES,"lookahead_features":False}
        dataset_hash=hashlib.sha256(raw).hexdigest(); run_id=hashlib.sha256(("stimpy-replay-v1|"+dataset_hash+"|"+symbol+"|"+timeframe+"|"+json.dumps(config,sort_keys=True)).encode()).hexdigest()
        existing=self.store.get_replay_run(run_id)
        if existing:return existing
        started=parse_timestamp(self.clock()); cases=[]; n=len(rows); boundaries=(int(n*.6),int(n*.8))
        for i in range(20,n-horizon):
            split=self._split(i,boundaries); outcome_split=self._split(i+horizon,boundaries)
            if split!=outcome_split: continue
            features=self._features(rows,i); signals=self._signals(rows,i,features)
            future_return=rows[i+horizon]["close"]/rows[i]["close"]-1
            for key,direction in signals:
                measured=abs(future_return) if direction=="MAGNITUDE" else future_return*(1 if direction=="LONG" else -1)
                outcome="SUPPORTING" if measured>=threshold else "CONTRADICTING" if measured<=-threshold else "NEUTRAL"
                canonical=f"{run_id}|{key}|{rows[i]['timestamp'].isoformat()}|{split}"
                cases.append({"case_id":hashlib.sha256(canonical.encode()).hexdigest(),"hypothesis_key":key,"split":split,"signal_at":rows[i]["timestamp"].isoformat(),"outcome_at":rows[i+horizon]["timestamp"].isoformat(),"direction":direction,"outcome":outcome,"entry_price":rows[i]["close"],"exit_price":rows[i+horizon]["close"],"return_value":future_return,"features":features})
        completed=parse_timestamp(self.clock()); counts={name:sum(c["outcome"]==name for c in cases) for name in ("SUPPORTING","CONTRADICTING","NEUTRAL")}
        run={"run_id":run_id,"dataset_hash":dataset_hash,"symbol":str(symbol)[:32],"timeframe":str(timeframe)[:16],"row_count":n,"case_count":len(cases),"supporting_count":counts["SUPPORTING"],"contradicting_count":counts["CONTRADICTING"],"neutral_count":counts["NEUTRAL"],"started_at":started.isoformat(),"completed_at":completed.isoformat(),"status":"COMPLETED","configuration":config}
        return self.store.save_replay(run,cases)
    def _load(self,path):
        if path.suffix.lower()!=".csv" or path.stat().st_size>100_000_000: raise ValueError("bounded CSV file required")
        rows=[]
        with path.open("r",encoding="utf-8-sig",newline="") as handle:
            reader=csv.DictReader(handle); required={"timestamp","open","high","low","close","volume"}
            if not reader.fieldnames or not required.issubset({h.strip().lower() for h in reader.fieldnames}): raise ValueError("CSV requires timestamp,open,high,low,close,volume")
            for raw in reader:
                data={str(k).strip().lower():v for k,v in raw.items()}; timestamp=parse_timestamp(data["timestamp"]); values={k:float(data[k]) for k in ("open","high","low","close","volume")}
                if not all(isfinite(v) for v in values.values()) or min(values[k] for k in ("open","high","low","close"))<=0 or values["volume"]<0 or values["high"]<max(values["open"],values["close"]) or values["low"]>min(values["open"],values["close"]): raise ValueError("invalid OHLCV row")
                if rows and timestamp<=rows[-1]["timestamp"]: raise ValueError("timestamps must be strictly increasing")
                rows.append({"timestamp":timestamp,**values})
        if len(rows)<30: raise ValueError("at least 30 chronological rows are required")
        return rows
    @staticmethod
    def _split(i,b): return "TRAIN" if i<b[0] else "VALIDATION" if i<b[1] else "TEST"
    @staticmethod
    def _features(rows,i):
        closes=[r["close"] for r in rows]; volumes=[r["volume"] for r in rows]; avg=lambda values,n:sum(values[i-n+1:i+1])/n
        returns=[closes[j]/closes[j-1]-1 for j in range(i-19,i+1)]; mean=sum(returns)/len(returns); volatility=sqrt(sum((x-mean)**2 for x in returns)/len(returns))
        return {"ma5":avg(closes,5),"ma10":avg(closes,10),"ma20":avg(closes,20),"prev_ma5":sum(closes[i-5:i])/5,"prev_ma10":sum(closes[i-10:i])/10,"prev_ma20":sum(closes[i-20:i])/20,"avg_volume20":avg(volumes,20),"volatility20":volatility,"hour":rows[i]["timestamp"].hour}
    @staticmethod
    def _signals(rows,i,f):
        c=rows[i]; previous=rows[i-20:i]; prior_high=max(r["high"] for r in previous); rising=f["ma5"]>f["prev_ma5"] and f["ma10"]>f["prev_ma10"] and f["ma20"]>f["prev_ma20"]; out=[]
        if c["close"]>f["ma5"]>f["ma10"]>f["ma20"] and rising: out.append(("trend_momentum","LONG"))
        if c["close"]>f["ma5"]*1.03: out.append(("overextended_momentum","SHORT"))
        if c["close"]>prior_high and c["volume"]>f["avg_volume20"]*1.5: out.append(("breakout","LONG"))
        if c["high"]>prior_high and c["close"]<prior_high: out.append(("false_breakout","SHORT"))
        if c["low"]<=prior_high<=c["close"]: out.append(("retest","LONG"))
        if f["volatility20"]>.02: out.append(("volatility","MAGNITUDE"))
        if c["volume"]>f["avg_volume20"]*1.25: out.append(("volume","LONG" if c["close"]>=c["open"] else "SHORT"))
        if f["ma5"]>f["ma10"]>f["ma20"]: out.append(("multi_timeframe","LONG"))
        if abs(f["ma5"]/f["ma20"]-1)>.02: out.append(("market_regime","MAGNITUDE"))
        if f["hour"] in {0,8,13,14,15}: out.append(("time_dependence","MAGNITUDE"))
        return out

"""Explicit read-only archive analysis for deduplicated Pandorick decisions and final paper outcomes."""
from __future__ import annotations
import hashlib,json,zipfile
from collections import defaultdict
from datetime import UTC,datetime
from math import isfinite
from pathlib import Path
from .models import parse_timestamp

SYMBOLS=("BTCUSDT","ETHUSDT","XRPUSDT")

class PandorickTrainingService:
    def __init__(self,store,clock=None):self.store=store;self.clock=clock or (lambda:datetime.now(UTC))
    def analyse_archive(self,path):
        path=Path(path);started=parse_timestamp(self.clock());decisions={};outcomes={}
        with zipfile.ZipFile(path) as archive:
            root=self._root(archive);decision_name=root+"platform_decisions.jsonl";outcome_name=root+"trade_outcomes.jsonl"
            infos=[archive.getinfo(decision_name),archive.getinfo(outcome_name)];fingerprint="|".join(f"{i.filename}:{i.CRC}:{i.file_size}" for i in infos);dataset_hash=hashlib.sha256(fingerprint.encode()).hexdigest()
            config={"symbols":SYMBOLS,"decision_entry":decision_name,"outcome_entry":outcome_name,"split":[.6,.2,.2],"final_closed_only":True,"price_status":"ok","automatic_evidence_promotion":False}
            run_id=hashlib.sha256(("stimpy-pandorick-training-v1|"+dataset_hash+"|"+json.dumps(config,sort_keys=True)).encode()).hexdigest();existing=self.store.get_pandorick_training_run(run_id)
            if existing:return existing
            with archive.open(decision_name) as stream:
                for raw in stream:
                    try:o=json.loads(raw);p=o.get("payload") or {};did=p.get("decision_id")
                    except Exception:continue
                    if did and p.get("symbol") in SYMBOLS and p.get("price_status")=="ok":decisions[did]=(o,p)
            with archive.open(outcome_name) as stream:
                for raw in stream:
                    try:o=json.loads(raw);p=o.get("payload") or {};did=p.get("decision_id")
                    except Exception:continue
                    if o.get("record_type")=="SIMULATED_TRADE_CLOSED" and did and p.get("symbol") in SYMBOLS:
                        if did not in outcomes or str(o.get("timestamp",""))>str(outcomes[did].get("timestamp","")):outcomes[did]=o
        linked=[]
        for did,outcome in outcomes.items():
            if did not in decisions:continue
            event,p=decisions[did];op=outcome["payload"];confidence=self._confidence(p.get("confidence",p.get("probability")));ret=self._number(op.get("gross_profit_percent"));result=str(op.get("result_type") or "BREAKEVEN").upper()
            if confidence is None or ret is None or result not in {"WIN","LOSS","BREAKEVEN"}:continue
            volatility,volume_ratio,regime=self._features(p);decision_at=parse_timestamp(event.get("created_at") or p.get("source_timestamp"));outcome_at=parse_timestamp(outcome.get("timestamp") or op.get("exit_time"))
            linked.append({"decision_id":did,"signal_id":op.get("signal_id"),"symbol":p["symbol"],"decision_at":decision_at,"outcome_at":outcome_at,"direction":str(p.get("direction") or op.get("direction") or "UNKNOWN"),"confidence":confidence,"result_type":result,"return_percent":ret,"volatility":volatility,"volume_ratio":volume_ratio,"market_regime":regime,"data_quality":"OK","features":{"price_source":p.get("price_source"),"strength":p.get("strength"),"volatility":volatility,"volume_ratio":volume_ratio,"market_regime":regime}})
        linked.sort(key=lambda c:(c["outcome_at"],c["decision_id"]));n=len(linked);boundaries=(int(n*.6),int(n*.8));cases=[]
        for i,c in enumerate(linked):
            c["split"]="TRAIN" if i<boundaries[0] else "VALIDATION" if i<boundaries[1] else "TEST";c["decision_at"]=c["decision_at"].isoformat();c["outcome_at"]=c["outcome_at"].isoformat();c["case_id"]=hashlib.sha256(f"{run_id}|{c['decision_id']}".encode()).hexdigest();cases.append(c)
        metrics=self._metrics(run_id,cases);completed=parse_timestamp(self.clock());run={"run_id":run_id,"dataset_hash":dataset_hash,"archive_name":path.name,"decision_count":len(decisions),"closed_outcome_count":len(outcomes),"linked_case_count":len(cases),"excluded_count":len(outcomes)-len(cases),"started_at":started.isoformat(),"completed_at":completed.isoformat(),"status":"COMPLETED","configuration":config}
        return self.store.save_pandorick_training(run,cases,metrics)
    @staticmethod
    def _root(archive):
        candidates=[n for n in archive.namelist() if n.endswith("platform_decisions.jsonl") and "/archive/" not in n]
        if len(candidates)!=1:raise ValueError("archive must contain one current platform_decisions.jsonl")
        return candidates[0][:-len("platform_decisions.jsonl")]
    @staticmethod
    def _number(value):
        try:value=float(value)
        except (TypeError,ValueError):return None
        return value if isfinite(value) else None
    @classmethod
    def _confidence(cls,value):
        value=cls._number(value)
        if value is None:return None
        value=value/100 if value>1 else value
        return value if 0<=value<=1 else None
    @classmethod
    def _features(cls,p):
        indicators=p.get("indicators") if isinstance(p.get("indicators"),dict) else {};facts=p.get("facts") if isinstance(p.get("facts"),dict) else {}
        volatility=cls._number(indicators.get("volatility"));volume_ratio=cls._number(indicators.get("volume_ratio"));trend=None
        if isinstance(facts.get("trend"),dict):trend=facts["trend"].get("value")
        if volume_ratio is None and isinstance(facts.get("volume"),dict):volume_ratio=cls._number((facts["volume"].get("evidence") or {}).get("ratio"))
        close=cls._number(indicators.get("close") or indicators.get("close_price") or p.get("analysis_close"));atr=cls._number(indicators.get("atr"))
        if volatility is None and close and atr is not None:volatility=atr/close
        if not trend:
            ma20=cls._number(indicators.get("ema20") or indicators.get("sma_20"));trend="UP" if close and ma20 and close>ma20 else "DOWN" if close and ma20 else "UNKNOWN"
        return volatility,volume_ratio,str(trend).upper()
    @staticmethod
    def _band(value,low,high):return "UNKNOWN" if value is None else "LOW" if value<low else "HIGH" if value>=high else "MEDIUM"
    @classmethod
    def _metrics(cls,run_id,cases):
        specs=(("confidence_calibration","confidence",lambda c:cls._band(c["confidence"],.55,.70)),("error_hypothesis","regime_volatility_confidence",lambda c:f"{c['market_regime']}|{cls._band(c['volatility'],.01,.03)}|{cls._band(c['confidence'],.55,.70)}"),("volatility","volatility",lambda c:cls._band(c["volatility"],.01,.03)),("volume","volume_ratio",lambda c:cls._band(c["volume_ratio"],.8,1.2)),("market_regime","market_regime",lambda c:c["market_regime"]))
        metrics=[]
        for key,dimension,bucket_fn in specs:
            for split in ("ALL","TRAIN","VALIDATION","TEST"):
                groups=defaultdict(list)
                for case in cases:
                    if split=="ALL" or case["split"]==split:groups[bucket_fn(case)].append(case)
                for bucket,items in groups.items():
                    wins=sum(c["result_type"]=="WIN" for c in items);losses=sum(c["result_type"]=="LOSS" for c in items);breakevens=len(items)-wins-losses;win_rate=wins/len(items);avg_return=sum(c["return_percent"] for c in items)/len(items);avg_conf=sum(c["confidence"] for c in items)/len(items);gap=win_rate-avg_conf if key=="confidence_calibration" else None;canonical=f"{run_id}|{key}|{dimension}|{bucket}|{split}"
                    metrics.append({"metric_id":hashlib.sha256(canonical.encode()).hexdigest(),"hypothesis_key":key,"dimension":dimension,"bucket":bucket,"split":split,"case_count":len(items),"win_count":wins,"loss_count":losses,"breakeven_count":breakevens,"win_rate":win_rate,"average_return":avg_return,"average_confidence":avg_conf,"calibration_gap":gap})
        return metrics

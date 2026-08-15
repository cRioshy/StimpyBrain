"""Explicit reaction-window recorder; no scheduler and no trading capability."""
from __future__ import annotations
from datetime import datetime
from .models import stable_id
from .reaction import ReactionAnalyzer

ALLOWED_WINDOWS={"T-30m","T-5m","T0","+5m","+30m","+2h","+24h"}
class SocialResearchService:
    def __init__(self,repository,hypothesis_min_cases=25):self.repository=repository;self.min_cases=hypothesis_min_cases;self.analyzer=ReactionAnalyzer()
    def record_market_snapshot(self,event_id,asset,window_label,price,snapshot_at:datetime,source,volume=None,volatility=None,market_regime="UNKNOWN"):
        if window_label not in ALLOWED_WINDOWS:raise ValueError("unsupported reaction window")
        if not self.repository.event(event_id):raise ValueError("unknown social event")
        snapshot_id=stable_id("social-snapshot",event_id,asset,window_label);self.repository.save_snapshot(event_id,asset,window_label,price,volume,volatility,market_regime,snapshot_at,source,snapshot_id)
        snapshots=self.repository.snapshots(event_id,asset);prices={x["window_label"]:x["price"] for x in snapshots};volumes={x["window_label"]:x["volume"] for x in snapshots if x["volume"] is not None};analysis=self.analyzer.analyze(event_id,asset,prices,volumes);self.repository.save_analysis(analysis);self.repository.set_event_status(event_id,"COMPLETED" if analysis.analysis_status=="COMPLETED" else "TRACKING")
        if analysis.analysis_status=="COMPLETED":self.repository.refresh_profiles(self.min_cases)
        return analysis

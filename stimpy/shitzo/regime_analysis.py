"""Read-only descriptive performance analysis grouped by entry-time regime."""
from __future__ import annotations

from datetime import datetime
from .models import FeatureSnapshot


class RegimeAnalysisService:
    def __init__(self,repository,classifier,min_cases=5):self.repository=repository;self.classifier=classifier;self.min_cases=max(1,int(min_cases))

    def backfill(self,limit=None):
        labels=[]
        for row in self.repository.unlabeled_snapshots(limit):
            features=row["features"]
            snapshot=FeatureSnapshot(row["snapshot_id"],row["symbol"],datetime.fromisoformat(row["snapshot_at"]),datetime.fromisoformat(row["window_started_at"]),datetime.fromisoformat(row["window_ended_at"]),features["price"],features["short_ma"],features["long_ma"],features["momentum"],features["volatility"],features["sample_count"],features["source"],tuple(row["source_data_ids"]),tuple(features.get("available_timeframes") or ()),features.get("market_regime"),features.get("data_quality","VALID"))
            labels.append(self.classifier.classify(snapshot,row["run_id"],"HISTORICAL_BACKFILL"))
        return self.repository.save_regime_labels(labels)

    def performance(self,run_id=None,trader_id=None,symbol=None): return self.repository.regime_performance(run_id,trader_id,symbol,self.min_cases)
    def losses(self,limit=100,offset=0,run_id=None,trader_id=None,symbol=None): return self.repository.regime_losses(limit,offset,run_id,trader_id,symbol)

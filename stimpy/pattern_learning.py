"""Explicit, explainable grouping of independent persisted cases."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC,datetime

from .models import Outcome,Pattern,PatternStatus,parse_timestamp


class PatternLearningService:
    def __init__(self,store,min_cases=25,supported_min_cases=50,max_provisional_confidence=.70,clock=None):
        self.store=store
        self.min_cases=max(2,int(min_cases))
        self.supported_min_cases=max(self.min_cases,int(supported_min_cases))
        self.max_provisional_confidence=max(0.0,min(float(max_provisional_confidence),.70))
        self.clock=clock or (lambda:datetime.now(UTC))

    def learn(self,observation_ids):
        if isinstance(observation_ids,(str,bytes)) or not isinstance(observation_ids,(tuple,list,set)): raise TypeError("observation_ids must be a collection")
        grouped={}
        for observation_id in dict.fromkeys(observation_ids):
            observation=self.store.get_observation(str(observation_id))
            if observation is None: raise KeyError("unknown observation")
            evidence=self.store.get_evidence_for_observation(observation["observation_id"])
            if evidence is None: raise ValueError("pattern cases require persisted evidence")
            conditions=self._conditions(observation)
            pattern_id=self._pattern_id(conditions)
            grouped.setdefault(pattern_id,[]).append((observation,evidence,conditions))
        results=[]
        for pattern_id,cases in grouped.items():
            created_at=parse_timestamp(self.clock())
            for observation,evidence,conditions in cases:
                self.store.add_pattern_case(pattern_id,"comparable_outcome",conditions,observation,evidence.evidence_id,created_at)
            results.append(self._refresh(pattern_id))
        return tuple(results)

    def get(self,pattern_id): return self.store.get_pattern(pattern_id)

    def _refresh(self,pattern_id):
        cases=self.store.list_pattern_cases(pattern_id)
        if not cases: raise KeyError("unknown pattern")
        positive=sum(case["outcome"]==Outcome.WIN.value for case in cases)
        negative=sum(case["outcome"]==Outcome.LOSS.value for case in cases)
        unresolved=len(cases)-positive-negative
        evidence_count=sum(bool(case["evidence_id"]) for case in cases)
        contradiction_count=negative
        decisive=positive+negative
        ratio=(max(positive,negative)/decisive) if decisive else 0.0
        status=PatternStatus.OBSERVED
        if len(cases)>=self.min_cases:
            status=PatternStatus.CONTRADICTED if negative>positive else PatternStatus.PROVISIONAL
        if len(cases)>=self.supported_min_cases and positive>0 and negative==0:
            status=PatternStatus.SUPPORTED
        confidence=min(ratio*(decisive/len(cases)),self._confidence_cap(status))
        previous=self.store.get_pattern(pattern_id); now=parse_timestamp(self.clock())
        pattern=Pattern(pattern_id,cases[0]["pattern_type"],json.loads(cases[0]["conditions"]),len(cases),positive,negative,unresolved,evidence_count,contradiction_count,confidence,status,previous.created_at if previous else now,now)
        return self.store.save_pattern(pattern)

    def _confidence_cap(self,status):
        if status is PatternStatus.OBSERVED: return min(.49,self.max_provisional_confidence)
        if status in {PatternStatus.PROVISIONAL,PatternStatus.CONTRADICTED}: return self.max_provisional_confidence
        return .90

    @staticmethod
    def _conditions(observation):
        payload=observation.get("payload") or {}
        regime=payload.get("market_regime",payload.get("regime","UNKNOWN"))
        if not isinstance(regime,str) or not regime.strip(): regime="UNKNOWN"
        return {"market":observation["market"].lower(),"symbol":observation["symbol"].upper(),"decision":str(observation.get("decision") or "UNKNOWN").upper(),"market_regime":regime.strip().upper()}

    @staticmethod
    def _pattern_id(conditions):
        canonical=json.dumps({"pattern_type":"comparable_outcome","conditions":conditions},sort_keys=True,separators=(",",":"),ensure_ascii=True)
        return hashlib.sha256(("stimpy-pattern-v1|"+canonical).encode()).hexdigest()

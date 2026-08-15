"""Conservative local hypothesis persistence and evaluation foundation."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC,datetime

from .models import (Hypothesis,HypothesisCreator,HypothesisEvaluation,HypothesisEvidence,
    HypothesisEvidenceDirection,HypothesisStatus,parse_timestamp)


_SECRET_ASSIGNMENT=re.compile(r"(?i)\b(token|password|authorization|cookie|secret|api[_-]?key)\s*[:=]")


class HypothesisEngine:
    def __init__(self,store,min_investigating_cases=5,min_provisional_cases=25,min_supported_cases=100,
                 min_supported_ratio=.70,max_contradicted_ratio=.30,max_text_chars=2000,clock=None):
        self.store=store
        self.min_investigating_cases=max(2,int(min_investigating_cases))
        self.min_provisional_cases=max(self.min_investigating_cases,int(min_provisional_cases))
        self.min_supported_cases=max(self.min_provisional_cases,int(min_supported_cases))
        self.min_supported_ratio=max(.50,min(float(min_supported_ratio),.95))
        self.max_contradicted_ratio=max(.05,min(float(max_contradicted_ratio),.50))
        self.max_text_chars=max(128,min(int(max_text_chars),10_000))
        self.clock=clock or (lambda:datetime.now(UTC))

    def create_hypothesis(self,statement,question,required_data,created_by="user"):
        statement=self._text(statement,"statement")
        question=self._text(question,"question")
        creator=HypothesisCreator(created_by)
        if isinstance(required_data,(str,bytes)) or not isinstance(required_data,(list,tuple,set)): raise TypeError("required_data must be a collection")
        normalized=tuple(sorted({self._data_name(item) for item in required_data}))
        if not normalized or len(normalized)>32: raise ValueError("required_data must contain 1 to 32 items")
        canonical={"statement":self._canonical_text(statement),"question":self._canonical_text(question),"required_data":normalized}
        hypothesis_id=hashlib.sha256(("stimpy-hypothesis-v1|"+json.dumps(canonical,sort_keys=True,separators=(",",":"),ensure_ascii=True)).encode()).hexdigest()
        existing=self.store.get_hypothesis(hypothesis_id)
        if existing is not None: return existing
        now=parse_timestamp(self.clock())
        return self.store.create_hypothesis(Hypothesis(hypothesis_id,statement,question,creator,now,now,normalized))

    def add_evidence(self,hypothesis_id,source,direction,strength,quality,description,source_observation_ids):
        hypothesis=self.store.get_hypothesis(str(hypothesis_id))
        if hypothesis is None: raise KeyError("unknown hypothesis")
        if hypothesis.status in {HypothesisStatus.REJECTED,HypothesisStatus.ARCHIVED}: raise ValueError("terminal hypothesis cannot receive evidence")
        source=self._short_text(source,"source",128); description=self._text(description,"description")
        direction=HypothesisEvidenceDirection(direction)
        strength=self._unit_interval(strength,"strength"); quality=self._unit_interval(quality,"quality")
        if isinstance(source_observation_ids,(str,bytes)) or not isinstance(source_observation_ids,(list,tuple,set)): raise TypeError("source_observation_ids must be a collection")
        observation_ids=tuple(sorted({str(item).strip() for item in source_observation_ids if str(item).strip()}))
        if not observation_ids or len(observation_ids)>100: raise ValueError("source_observation_ids must contain 1 to 100 IDs")
        observations=[]
        for observation_id in observation_ids:
            observation=self.store.get_observation(observation_id)
            if observation is None: raise KeyError("unknown source observation")
            observations.append(observation)
        origin_keys=tuple(sorted({str(row["correlation_id"]) for row in observations}))
        if len(origin_keys)!=1: raise ValueError("one evidence item must represent exactly one independent origin")
        independence_key=hashlib.sha256(("stimpy-hypothesis-case-v1|"+json.dumps(origin_keys,separators=(",",":"))).encode()).hexdigest()
        canonical={"hypothesis_id":hypothesis.hypothesis_id,"source":source,"direction":direction.value,"strength":strength,"quality":quality,"description":description,"observation_ids":observation_ids}
        evidence_id=hashlib.sha256(("stimpy-hypothesis-evidence-v1|"+json.dumps(canonical,sort_keys=True,separators=(",",":"),ensure_ascii=True)).encode()).hexdigest()
        existing=self.store.get_hypothesis_evidence(evidence_id)
        if existing is not None: return existing
        now=parse_timestamp(self.clock()); observed_at=max(parse_timestamp(row["source_timestamp"]) for row in observations)
        candidate=HypothesisEvidence(evidence_id,hypothesis.hypothesis_id,source,observation_ids,direction,strength,quality,description,observed_at,now,independence_key)
        return self.store.add_hypothesis_evidence(candidate)

    def evaluate_hypothesis(self,hypothesis_id):
        hypothesis=self.store.get_hypothesis(str(hypothesis_id))
        if hypothesis is None: raise KeyError("unknown hypothesis")
        if hypothesis.status in {HypothesisStatus.REJECTED,HypothesisStatus.ARCHIVED}: raise ValueError("terminal hypothesis cannot be evaluated")
        evidence=self.store.load_hypothesis_evidence(hypothesis.hypothesis_id)
        supporting=[item for item in evidence if item.direction is HypothesisEvidenceDirection.SUPPORTING]
        contradicting=[item for item in evidence if item.direction is HypothesisEvidenceDirection.CONTRADICTING]
        neutral=[item for item in evidence if item.direction is HypothesisEvidenceDirection.NEUTRAL]
        weighted_support=sum(item.strength*item.quality for item in supporting)
        weighted_contradiction=sum(item.strength*item.quality for item in contradicting)
        decisive_weight=weighted_support+weighted_contradiction
        ratio=weighted_support/decisive_weight if decisive_weight else 0.0
        count=len(evidence); source_count=len({item.source.lower() for item in evidence})
        quality=sum(item.quality for item in evidence)/count if count else 0.0
        status=self._status(count,ratio,quality,source_count)
        consistency=max(ratio,1.0-ratio) if decisive_weight else 0.0
        sample_factor=min(1.0,count/self.min_supported_cases)
        source_factor=min(1.0,source_count/3.0)
        confidence=min(consistency*quality*(.8*sample_factor+.2*source_factor),self._confidence_cap(status))
        uncertainty=1.0-confidence; now=parse_timestamp(self.clock())
        evidence_ids=tuple(sorted(item.evidence_id for item in evidence))
        rules=(self.min_investigating_cases,self.min_provisional_cases,self.min_supported_cases,self.min_supported_ratio,self.max_contradicted_ratio)
        evaluation_id=hashlib.sha256(("stimpy-hypothesis-evaluation-v1|"+hypothesis.hypothesis_id+"|"+json.dumps((evidence_ids,rules),separators=(",",":"))).encode()).hexdigest()
        explanation=self._explanation(status,count,ratio,quality,source_count)
        evaluation=HypothesisEvaluation(evaluation_id,hypothesis.hypothesis_id,status,ratio,confidence,len(supporting),len(contradicting),len(neutral),weighted_support,weighted_contradiction,quality,uncertainty,source_count,count,explanation,now)
        stored=self.store.save_hypothesis_evaluation(evaluation)
        self.store.update_hypothesis_evaluation(hypothesis.hypothesis_id,stored.status,stored.confidence,stored.independent_case_count,stored.contradicting_count,stored.neutral_count,stored.evaluated_at)
        return stored

    def _status(self,count,ratio,quality,source_count):
        if count==0: return HypothesisStatus.NEW
        if count<self.min_provisional_cases: return HypothesisStatus.INVESTIGATING
        if ratio<=self.max_contradicted_ratio: return HypothesisStatus.CONTRADICTED
        if count>=self.min_supported_cases and ratio>=self.min_supported_ratio and quality>=.60 and source_count>=2: return HypothesisStatus.SUPPORTED
        if ratio>=self.min_supported_ratio: return HypothesisStatus.PROVISIONAL
        return HypothesisStatus.INVESTIGATING

    @staticmethod
    def _confidence_cap(status):
        if status is HypothesisStatus.NEW: return 0.0
        if status is HypothesisStatus.INVESTIGATING: return .49
        if status in {HypothesisStatus.PROVISIONAL,HypothesisStatus.CONTRADICTED}: return .70
        return .90

    def _explanation(self,status,count,ratio,quality,source_count):
        return (f"Descriptive non-causal evaluation: status {status.value}; {count} independent cases; "
                f"support ratio {ratio:.3f}; mean quality {quality:.3f}; {source_count} sources. "
                "SUPPORTED would still mean supported by current evidence, not proven or predictive.")

    def _text(self,value,name): return self._short_text(value,name,self.max_text_chars)

    @staticmethod
    def _canonical_text(value): return " ".join(value.casefold().split())

    @staticmethod
    def _short_text(value,name,limit):
        if not isinstance(value,str): raise TypeError(f"{name} must be text")
        value=" ".join(value.split())
        if not value: raise ValueError(f"{name} must not be empty")
        if len(value)>limit: raise ValueError(f"{name} exceeds size limit")
        if _SECRET_ASSIGNMENT.search(value): raise ValueError(f"{name} appears to contain a secret")
        return value

    @staticmethod
    def _data_name(value):
        if not isinstance(value,str): raise TypeError("required_data items must be text")
        value=value.strip().lower()
        if not re.fullmatch(r"[a-z0-9][a-z0-9_.-]{0,63}",value): raise ValueError("invalid required_data item")
        return value

    @staticmethod
    def _unit_interval(value,name):
        if isinstance(value,bool) or not isinstance(value,(int,float)): raise TypeError(f"{name} must be numeric")
        value=float(value)
        if not 0.0<=value<=1.0: raise ValueError(f"{name} must be between 0 and 1")
        return value

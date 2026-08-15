"""Transparent heuristic evidence scoring; never a probability model."""
import hashlib
from dataclasses import dataclass
from .models import EvidenceResult,Observation,utc_now

@dataclass(frozen=True)
class EvidenceRules:
    high_confidence_threshold:float=.8
    high_confidence_points:int=2
    positive_profit_points:int=3
    win_points:int=2
    loss_points:int=-3
    high_confidence_loss_points:int=-2
    minimum_score:int=-5
    maximum_score:int=7
    schema_version:int=1

class EvidenceEngine:
    def __init__(self,rules=None): self.rules=rules or EvidenceRules()
    def evaluate(self,observation:Observation)->EvidenceResult:
        if observation.confidence is None: raise ValueError("prototype observation required")
        r=self.rules; score=0; supporting=[]; contradicting=[]
        if observation.confidence>r.high_confidence_threshold: score+=r.high_confidence_points; supporting.append("reported confidence exceeds configured threshold")
        if observation.profit>0: score+=r.positive_profit_points; supporting.append("reported profit is positive")
        if observation.outcome=="WIN": score+=r.win_points; supporting.append("reported outcome is WIN")
        if observation.outcome=="LOSS": score+=r.loss_points; contradicting.append("reported outcome is LOSS")
        if observation.outcome=="LOSS" and observation.confidence>r.high_confidence_threshold: score+=r.high_confidence_loss_points; contradicting.append("high reported confidence conflicts with LOSS")
        normalized=max(0.0,min(1.0,(score-r.minimum_score)/(r.maximum_score-r.minimum_score)))
        final_outcome=observation.outcome in {"WIN","LOSS","EXPIRED","CANCELLED"}
        quality_score=1.0 if final_outcome else .75
        evidence_id=hashlib.sha256(f"evidence|v{r.schema_version}|{observation.observation_id}".encode()).hexdigest()
        return EvidenceResult(score,normalized,tuple(supporting),tuple(contradicting),len(supporting)+len(contradicting),utc_now(),evidence_id,observation.observation_id,quality_score,r.schema_version)

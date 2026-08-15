"""Non-causal reasoning over one observation and its transparent evidence."""
import hashlib
from .models import EvidenceResult,Observation,ReasoningResult,utc_now

class ReasoningEngine:
    def think(self,observation:Observation,evidence:EvidenceResult)->ReasoningResult:
        reasons=list(evidence.supporting_evidence); counter=list(evidence.contradicting_evidence)
        counter.append("a single observation cannot establish a causal pattern")
        if evidence.evidence_count<3: counter.append("evidence count is low")
        if observation.confidence>.9: counter.append("reported confidence may be over-weighted")
        uncertainty=max(.25,1.0-evidence.normalized_score) if evidence.score>=0 else min(1.0,.6+abs(evidence.score)/10)
        confidence=max(0.0,min(.75,evidence.normalized_score*(1.0-uncertainty/2)))
        if evidence.score>0: conclusion="This case contains provisional supporting evidence; no causal or trading conclusion follows."
        elif evidence.score<0: conclusion="This case contains contradictory evidence and should remain an observation."
        else: conclusion="This case is inconclusive and requires additional independent observations."
        assumptions=("reported outcome and profit use consistent source semantics",)
        missing=["independent historical comparison cases"]
        if observation.outcome in {"OPEN","UNKNOWN"}: missing.append("validated final outcome")
        reasoning_id=hashlib.sha256(f"reasoning|v1|{observation.observation_id}|{evidence.evidence_id}".encode()).hexdigest()
        return ReasoningResult(observation.observation_id,evidence.score,tuple(reasons),tuple(counter),conclusion,confidence,uncertainty,utc_now(),reasoning_id,evidence.evidence_id,assumptions,tuple(missing),1)

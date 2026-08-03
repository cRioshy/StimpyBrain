"""Versioned Stimpy domain records."""
from __future__ import annotations
from dataclasses import dataclass,field
from datetime import UTC,datetime
from enum import StrEnum
from math import isfinite
from typing import Any

def utc_now(): return datetime.now(UTC)
def parse_timestamp(value):
    parsed=value if isinstance(value,datetime) else datetime.fromisoformat(str(value).replace("Z","+00:00"))
    if parsed.tzinfo is None: raise ValueError("timestamp must be timezone-aware")
    return parsed.astimezone(UTC)
def reject_non_finite(value):
    if isinstance(value,float) and not isfinite(value): raise ValueError("NaN and Infinity are forbidden")
    if isinstance(value,dict):
        for item in value.values(): reject_non_finite(item)
    elif isinstance(value,(list,tuple)):
        for item in value: reject_non_finite(item)

class SourceType(StrEnum):
    SYSTEM="system"; SERVICE="service"; DECISION="decision"; SIGNAL="signal"; OUTCOME="outcome"; BRAIN="brain"; FEATURE="feature"; STATISTICS="statistics"; GRAPH="graph"; ERROR="error"; HEARTBEAT="heartbeat"
class MemoryStatus(StrEnum):
    OBSERVED="OBSERVED"; REPEATED="REPEATED"; PROVISIONAL="PROVISIONAL"; SUPPORTED="SUPPORTED"; CONTRADICTED="CONTRADICTED"; ARCHIVED="ARCHIVED"
class Decision(StrEnum):
    LONG="LONG"; SHORT="SHORT"; HOLD="HOLD"; WAIT="WAIT"; UNKNOWN="UNKNOWN"
class Outcome(StrEnum):
    WIN="WIN"; LOSS="LOSS"; OPEN="OPEN"; EXPIRED="EXPIRED"; CANCELLED="CANCELLED"; UNKNOWN="UNKNOWN"
class KnowledgeStatus(StrEnum):
    OBSERVED="OBSERVED"; PROVISIONAL="PROVISIONAL"; SUPPORTED="SUPPORTED"; CONTRADICTED="CONTRADICTED"
class CriticSeverity(StrEnum):
    INFO="INFO"; LOW="LOW"; MEDIUM="MEDIUM"; HIGH="HIGH"; CRITICAL="CRITICAL"
class IncubationStatus(StrEnum):
    NEW="NEW"; INCUBATING="INCUBATING"; READY="READY"; RESOLVED="RESOLVED"; FAILED="FAILED"; CANCELLED="CANCELLED"

@dataclass(frozen=True)
class Observation:
    observation_id:str; event_id:str; correlation_id:str; source:str; source_endpoint:str; source_type:str
    observed_at:datetime; source_timestamp:datetime; symbol:str; market:str; payload:dict[str,Any]
    content_hash:str; schema_version:int=1
    decision:str|None=None; confidence:float|None=None; outcome:str|None=None; profit:float|None=None
    def __post_init__(self):
        for name in ("observation_id","event_id","correlation_id","source","source_endpoint","source_type","symbol","market","content_hash"):
            if not str(getattr(self,name)).strip(): raise ValueError(f"{name} must not be empty")
        SourceType(self.source_type); reject_non_finite(self.payload)
        if self.observed_at.tzinfo is None or self.source_timestamp.tzinfo is None: raise ValueError("timestamps must be aware")
        if self.schema_version!=1: raise ValueError("unsupported observation schema")
        prototype_values=(self.decision,self.confidence,self.outcome,self.profit)
        if any(value is not None for value in prototype_values):
            if not all(value is not None for value in prototype_values): raise ValueError("prototype observation fields must be complete")
            Decision(self.decision); Outcome(self.outcome)
            if isinstance(self.confidence,bool) or not isinstance(self.confidence,(int,float)): raise TypeError("confidence must be numeric")
            if not 0.0<=float(self.confidence)<=1.0: raise ValueError("confidence must be between 0 and 1")
            if isinstance(self.profit,bool) or not isinstance(self.profit,(int,float)): raise TypeError("profit must be numeric")
            if not isfinite(float(self.profit)): raise ValueError("profit must be finite")
    @property
    def timestamp(self): return self.source_timestamp

@dataclass(frozen=True)
class MemoryRecord:
    memory_id:str; memory_type:str; created_at:datetime; updated_at:datetime; source_observation_ids:tuple[str,...]
    subject:str; relation:str; object:str; evidence_count:int; contradiction_count:int; confidence:float
    status:MemoryStatus; last_verified_at:datetime; content:dict[str,Any]=field(default_factory=dict); schema_version:int=1

@dataclass(frozen=True)
class EvidenceResult:
    score:int; normalized_score:float; supporting_evidence:tuple[str,...]; contradicting_evidence:tuple[str,...]
    evidence_count:int; created_at:datetime; evidence_id:str=""; observation_id:str=""; quality_score:float=0.0; schema_version:int=1
    def __post_init__(self):
        if not self.evidence_id or not self.observation_id: raise ValueError("evidence and observation IDs are required")
        if self.schema_version!=1: raise ValueError("unsupported evidence schema")
        if self.created_at.tzinfo is None: raise ValueError("evidence timestamp must be aware")
        if self.evidence_count<0: raise ValueError("evidence_count must not be negative")
        for name in ("normalized_score","quality_score"):
            value=float(getattr(self,name))
            if not isfinite(value) or not 0.0<=value<=1.0: raise ValueError(f"{name} must be between 0 and 1")
    @property
    def raw_score(self): return self.score

@dataclass(frozen=True)
class ReasoningResult:
    observation_id:str; evidence_score:int; reasons:tuple[str,...]; counterarguments:tuple[str,...]
    conclusion:str; confidence:float; uncertainty:float; created_at:datetime; reasoning_id:str=""; evidence_id:str=""
    assumptions:tuple[str,...]=(); missing_information:tuple[str,...]=(); schema_version:int=1
    def __post_init__(self):
        if not self.reasoning_id or not self.observation_id or not self.evidence_id: raise ValueError("reasoning, observation and evidence IDs are required")
        if self.schema_version!=1: raise ValueError("unsupported reasoning schema")
        if self.created_at.tzinfo is None: raise ValueError("reasoning timestamp must be aware")
        if not self.conclusion.strip(): raise ValueError("reasoning conclusion is required")
        for name in ("confidence","uncertainty"):
            value=float(getattr(self,name))
            if not isfinite(value) or not 0.0<=value<=1.0: raise ValueError(f"{name} must be between 0 and 1")

@dataclass(frozen=True)
class CriticResult:
    observation_id:str; issues:tuple[str,...]; severity:str; suggestions:tuple[str,...]; created_at:datetime
    critic_id:str=""; reasoning_id:str=""; calibration_warning:bool=False; schema_version:int=1
    def __post_init__(self):
        if not self.critic_id or not self.observation_id or not self.reasoning_id: raise ValueError("critic, observation and reasoning IDs are required")
        CriticSeverity(self.severity)
        if self.schema_version!=1: raise ValueError("unsupported critic schema")
        if self.created_at.tzinfo is None: raise ValueError("critic timestamp must be aware")

@dataclass(frozen=True)
class KnowledgeEntry:
    knowledge_id:str; observation_id:str; symbol:str; decision:str; evidence_score:int
    reasons:tuple[str,...]; counterarguments:tuple[str,...]; critic_issues:tuple[str,...]
    status:KnowledgeStatus; created_at:datetime; schema_version:int=1; reasoning_id:str=""; critic_id:str=""

@dataclass(frozen=True)
class PrototypeResult:
    observation:Observation; stored:bool; evidence:EvidenceResult; reasoning:ReasoningResult
    critic:CriticResult; knowledge_entry:KnowledgeEntry

@dataclass(frozen=True)
class IncubationComparison:
    initial_evidence_score:int; final_evidence_score:int; score_delta:int
    initial_confidence:float; final_confidence:float; confidence_delta:float
    initial_decision:str; final_decision:str; direction_changed:bool
    initial_conclusion:str; final_conclusion:str

@dataclass(frozen=True)
class IncubationTask:
    incubation_id:str; subject:str; question:str; initial_observation_id:str; initial_reasoning_id:str
    status:IncubationStatus; created_at:datetime; reactivate_at:datetime; reactivated_at:datetime|None=None
    final_reasoning_id:str|None=None; new_observation_ids:tuple[str,...]=(); conclusion:str|None=None
    comparison:IncubationComparison|None=None; failure_count:int=0; last_error:str|None=None; schema_version:int=1
    def __post_init__(self):
        for name in ("incubation_id","subject","question","initial_observation_id","initial_reasoning_id"):
            if not str(getattr(self,name)).strip(): raise ValueError(f"{name} must not be empty")
        if self.created_at.tzinfo is None or self.reactivate_at.tzinfo is None: raise ValueError("incubation timestamps must be aware")
        if self.reactivated_at is not None and self.reactivated_at.tzinfo is None: raise ValueError("reactivated_at must be aware")
        if self.reactivate_at<self.created_at: raise ValueError("reactivate_at must not precede created_at")
        if self.failure_count<0: raise ValueError("failure_count must not be negative")
        if self.schema_version!=1: raise ValueError("unsupported incubation schema")

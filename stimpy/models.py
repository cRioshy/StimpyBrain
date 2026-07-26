"""Versioned Phase-2 domain records."""
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

@dataclass(frozen=True)
class Observation:
    observation_id:str; event_id:str; correlation_id:str; source:str; source_endpoint:str; source_type:str
    observed_at:datetime; source_timestamp:datetime; symbol:str; market:str; payload:dict[str,Any]
    content_hash:str; schema_version:int=1
    def __post_init__(self):
        for name in ("observation_id","event_id","correlation_id","source","source_endpoint","source_type","symbol","market","content_hash"):
            if not str(getattr(self,name)).strip(): raise ValueError(f"{name} must not be empty")
        SourceType(self.source_type); reject_non_finite(self.payload)
        if self.observed_at.tzinfo is None or self.source_timestamp.tzinfo is None: raise ValueError("timestamps must be aware")
        if self.schema_version!=1: raise ValueError("unsupported observation schema")

@dataclass(frozen=True)
class MemoryRecord:
    memory_id:str; memory_type:str; created_at:datetime; updated_at:datetime; source_observation_ids:tuple[str,...]
    subject:str; relation:str; object:str; evidence_count:int; contradiction_count:int; confidence:float
    status:MemoryStatus; last_verified_at:datetime; content:dict[str,Any]=field(default_factory=dict); schema_version:int=1

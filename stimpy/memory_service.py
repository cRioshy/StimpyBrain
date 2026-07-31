"""Evidence-counted memory without causal claims or model mutation."""
from __future__ import annotations
import hashlib,json
from datetime import UTC,datetime
from .models import MemoryRecord,MemoryStatus

class MemoryService:
    def __init__(self,store,events=None): self.store=store; self.events=events
    def update_from_observation(self,row):
        payload=row.get("payload",{}); subject=row.get("symbol") or "SYSTEM"; source_type=row["source_type"]
        if source_type=="decision": relation="decision_direction"; obj=str(payload.get("direction") or "UNKNOWN")
        elif source_type=="outcome": relation="outcome"; obj=str(payload.get("outcome") or payload.get("result") or "UNKNOWN")
        else: relation="observed_as"; obj=source_type
        memory_id=hashlib.sha256(f"{subject}|{relation}|{obj}".encode()).hexdigest(); current=self.store.get_memory(memory_id); now=datetime.now(UTC)
        ids=list(json.loads(current["source_observation_ids"])) if current else []
        if row["observation_id"] not in ids: ids.append(row["observation_id"])
        evidence=len(ids); contradictions=sum(int(other["evidence_count"]) for other in self.store.memories_for(subject,relation) if other["memory_id"]!=memory_id)
        confidence=min(.95,evidence/(evidence+3)); status=MemoryStatus.CONTRADICTED if contradictions else (MemoryStatus.SUPPORTED if evidence>=5 else MemoryStatus.REPEATED if evidence>=2 else MemoryStatus.OBSERVED)
        record=MemoryRecord(memory_id,"evidence_relation",datetime.fromisoformat(current["created_at"]) if current else now,now,tuple(ids),subject,relation,obj,evidence,contradictions,confidence,status,now,{"source_type":source_type,"causal":False},1)
        self.store.upsert_memory(record)
        if self.events: self.events.emit("STIMPY_MEMORY_UPDATED",memory_id=memory_id,evidence_count=evidence)
        return record
    def process_recent(self,limit=100): return [self.update_from_observation(row) for row in reversed(self.store.list(limit))]
    def snapshot(self,limit=100,offset=0):
        rows=self.store.list_memories(limit,offset); return {"count":self.store.count("memories"),"items":rows,"causal_claims":0}

class Memory:
    """Observation-memory facade backed by the existing JSONL/SQLite store."""
    def __init__(self,store): self.store=store
    def remember(self,observation): return self.store.append(observation)[0]
    def exists(self,observation_id): return self.store.exists(observation_id)
    def load_recent(self,limit=100): return self.store.load_recent(limit)

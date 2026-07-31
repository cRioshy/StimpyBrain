"""Bounded in-memory internal event journal."""
from collections import deque
from datetime import UTC,datetime
class InternalEvents:
    ALLOWED=frozenset({"STIMPY_OBSERVATION_RECEIVED","STIMPY_OBSERVATION_STORED","STIMPY_OBSERVATION_DUPLICATE","STIMPY_OBSERVATION_INVALID","STIMPY_SOURCE_UNAVAILABLE","STIMPY_SOURCE_RECOVERED","STIMPY_BATCH_COMPLETED","STIMPY_WORKFLOW_EVALUATED","STIMPY_MEMORY_UPDATED"})
    def __init__(self,limit=1000): self._items=deque(maxlen=limit)
    def emit(self,name,**data):
        if name not in self.ALLOWED: raise ValueError("unknown internal event")
        self._items.append({"name":name,"at":datetime.now(UTC).isoformat(),"data":data})
    def recent(self,limit=100): return list(self._items)[-max(1,min(limit,1000)):]

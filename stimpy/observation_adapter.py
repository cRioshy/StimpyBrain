"""Explicit, inactive-by-default adapter for allowlisted Pandorick events."""
from __future__ import annotations
from datetime import UTC, datetime
from .models import Observation, parse_timestamp

class ObservationAdapter:
    def __init__(self, store, topics): self.store, self.topics = store, frozenset(topics)
    def observe_event(self, event: dict) -> bool:
        try:
            if event.get("topic") not in self.topics: return False
            stamp=parse_timestamp(event["observed_at"])
            if stamp > datetime.now(UTC): return False
            item=Observation(str(event["event_id"]),str(event["correlation_id"]),str(event["topic"]),str(event.get("source","Pandorick")),str(event["market"]),str(event["symbol"]),stamp,dict(event.get("payload",{})))
            return self.store.append(item)
        except (KeyError, TypeError, ValueError): return False
    def source_unavailable(self) -> bool: return False

"""Read-only deterministic memory projections."""
from collections import Counter, defaultdict
class MemoryService:
    def __init__(self, store): self.store=store
    def snapshot(self):
        rows=list(reversed(self.store.list(10000))); topics=Counter(r["topic"] for r in rows); symbols=Counter(r["symbol"] for r in rows)
        transitions=Counter(f"{a['topic']}->{b['topic']}" for a,b in zip(rows,rows[1:]) if a["correlation_id"]==b["correlation_id"])
        decisions=defaultdict(dict)
        for r in rows: decisions[r["correlation_id"]][r["topic"]]=r["payload"]
        contradictions=sum(1 for v in decisions.values() if v.get("BRAIN_DECISION_RECEIVED",{}).get("decision") != v.get("DECISION_CREATED",{}).get("decision") and "BRAIN_DECISION_RECEIVED" in v and "DECISION_CREATED" in v)
        return {"observation_count":len(rows),"topic_counts":dict(topics),"symbol_counts":dict(symbols),"transitions":dict(transitions),"contradictions":contradictions}

"""Descriptive patterns only; correlation is explicitly not causation."""
from collections import Counter
class LearningService:
    def __init__(self,memory): self.memory=memory
    def analyze(self,limit=100):
        snapshot=self.memory.snapshot(limit); relations=Counter(item["relation"] for item in snapshot["items"])
        return {"mode":"evidence_descriptive_only","model_updates":0,"causal_claims":0,"pattern_counts":dict(relations),"memory":snapshot}

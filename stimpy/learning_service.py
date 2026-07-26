"""Phase-1 aggregation only; never mutates models or Pandorick."""
class LearningService:
    def __init__(self, memory): self.memory=memory
    def analyze(self): return {"mode":"descriptive_only","model_updates":0,"memory":self.memory.snapshot()}

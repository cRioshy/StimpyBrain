"""In-process read-only API facade (no mutation routes)."""
class ReadOnlyAPI:
    def __init__(self, store, memory, learning, graph): self.store,self.memory,self.learning,self.graph=store,memory,learning,graph
    def observations(self, limit=100): return self.store.list(limit)
    def memory_snapshot(self): return self.memory.snapshot()
    def learning_snapshot(self): return self.learning.analyze()
    def knowledge_graph(self): return self.graph()

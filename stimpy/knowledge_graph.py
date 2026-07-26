"""Read-only StimpyBrain knowledge graph projection."""
def build_graph():
    nodes=["StimpyBrain","ObservationAdapter","ObservationStore","MemoryService","LearningService","WorkflowGate","KnowledgeGraph","ReadOnlyAPI","Pandorick"]
    edges=[("Pandorick","ObservationAdapter","read-only events"),("ObservationAdapter","ObservationStore","append"),("ObservationStore","MemoryService","read"),("MemoryService","LearningService","aggregate"),("LearningService","KnowledgeGraph","project"),("KnowledgeGraph","ReadOnlyAPI","query")]
    return {"cluster":"StimpyBrain","nodes":nodes,"edges":[{"from":a,"to":b,"label":c} for a,b,c in edges]}

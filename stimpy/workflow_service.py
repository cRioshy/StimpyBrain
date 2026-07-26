from .workflow.models import WorkflowDefinition
from .workflow.nodes import PHASE1_NODES
from .workflow.registry import NodeRegistry
from .workflow.runner import WorkflowRunner
from .workflow.repository import SQLiteWorkflowRepository

class WorkflowService:
    def __init__(self, path):
        registry=NodeRegistry()
        for cls in PHASE1_NODES: registry.register(cls())
        self.repository=SQLiteWorkflowRepository(path); self.runner=WorkflowRunner(registry,self.repository)
        self.workflow=WorkflowDefinition("stimpy-phase1","Stimpy Observe",1,("DataQuality","Features","Prediction","MomentumGate","RiskGate","DecisionGate"),"observe",1)
    async def observe(self,data,**ids): return await self.runner.run(self.workflow,data,**ids)

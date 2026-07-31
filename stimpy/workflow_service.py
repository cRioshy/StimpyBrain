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
    async def evaluate_observation(self,row):
        payload=dict(row.get("payload",{})); required={"price","previous_price","volume","timestamp"}
        if not required.issubset(payload):
            return {"id":"shadow:"+row["observation_id"],"status":"REJECTED","reasons":["insufficient market fields for strict workflow"],"gates":["DataQuality"],"orders_created":0}
        result=await self.observe(payload,event_id="shadow:"+row["event_id"],correlation_id="shadow:"+row["correlation_id"],market=row["market"],symbol=row["symbol"])
        return {"id":result.execution_id,"status":result.status.value,"reasons":[result.reason] if result.reason else [],"gates":list(self.workflow.nodes),"orders_created":0}

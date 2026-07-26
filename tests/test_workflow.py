import asyncio, json, sqlite3, tempfile, unittest
from datetime import UTC, datetime
from pathlib import Path
from stimpy.workflow.models import WorkflowDefinition, ExecutionStatus
from stimpy.workflow.validator import WorkflowValidator, REQUIRED_TOPOLOGY
from stimpy.workflow.sanitizer import AuditSanitizer
from stimpy.workflow_service import WorkflowService
from stimpy.workflow.nodes import PHASE1_NODES, DataQualityNode
from stimpy.workflow.registry import NodeRegistry
from stimpy.workflow.repository import SQLiteWorkflowRepository
from stimpy.workflow.runner import WorkflowRunner

class SlowDataQuality(DataQualityNode):
    timeout_seconds=.01
    async def execute(self, context, data):
        await asyncio.sleep(1)

def custom_runner(path, first):
    registry=NodeRegistry()
    for cls in PHASE1_NODES: registry.register(first if cls is DataQualityNode else cls())
    return WorkflowRunner(registry,SQLiteWorkflowRepository(path))

class WorkflowTests(unittest.TestCase):
    def definition(self,nodes=REQUIRED_TOPOLOGY,mode="observe"):
        return WorkflowDefinition("w","workflow",1,tuple(nodes),mode,1)
    def test_exact_topology(self): WorkflowValidator.validate(self.definition())
    def test_optional_paper_final(self): WorkflowValidator.validate(self.definition(REQUIRED_TOPOLOGY+("PaperSimulation",)))
    def test_missing_decision_gate(self):
        with self.assertRaises(ValueError): WorkflowValidator.validate(self.definition(REQUIRED_TOPOLOGY[:-1]))
    def test_duplicate_gate(self):
        with self.assertRaises(ValueError): WorkflowValidator.validate(self.definition(REQUIRED_TOPOLOGY+("DecisionGate",)))
    def test_live_impossible(self):
        with self.assertRaises(ValueError): WorkflowValidator.validate(self.definition(mode="live"))
    def test_sanitizer_secrets_paths_binary_and_size(self):
        clean=AuditSanitizer(max_bytes=300,preview_chars=20).sanitize({"token":"x","local_path":"c:/secret","blob":b"abc","text":"x"*1000})
        encoded=json.dumps(clean); self.assertNotIn('"x"',encoded); self.assertNotIn("c:/secret",encoded); self.assertLess(len(encoded),500); self.assertIn("sha256",encoded)
    def test_observe_run_and_idempotency(self):
        with tempfile.TemporaryDirectory() as td:
            svc=WorkflowService(Path(td)/"db.sqlite")
            data={"price":101,"previous_price":100,"volume":2,"timestamp":datetime.now(UTC).isoformat()}
            args={"event_id":"e1","correlation_id":"c1","market":"crypto","symbol":"BTC"}
            first=asyncio.run(svc.observe(data,**args)); second=asyncio.run(svc.observe(data,**args))
            self.assertEqual(first.status,ExecutionStatus.COMPLETED); self.assertEqual(first.final_data["orders_created"],0); self.assertTrue(second.duplicate)
            row=svc.repository.get_execution(first.execution_id); self.assertNotEqual(row["status"],"RUNNING"); self.assertTrue(svc.repository.foreign_keys_enabled); self.assertEqual(svc.repository.schema_version,1)
            svc.repository.close()
    def test_nan_inf_negative_rejected(self):
        for bad in (float("nan"),float("inf"),-1):
            with self.subTest(bad=bad), tempfile.TemporaryDirectory() as td:
                svc=WorkflowService(Path(td)/"x.db"); data={"price":bad,"previous_price":100,"volume":2,"timestamp":datetime.now(UTC).isoformat()}
                out=asyncio.run(svc.observe(data,event_id="e",correlation_id="c",market="crypto",symbol="BTC")); self.assertEqual(out.status,ExecutionStatus.FAILED)
                svc.repository.close()
    def test_future_timestamp_rejected(self):
        from datetime import timedelta
        with tempfile.TemporaryDirectory() as td:
            svc=WorkflowService(Path(td)/"x.db"); data={"price":101,"previous_price":100,"volume":2,"timestamp":(datetime.now(UTC)+timedelta(hours=1)).isoformat()}
            out=asyncio.run(svc.observe(data,event_id="e",correlation_id="c",market="crypto",symbol="BTC")); self.assertEqual(out.status,ExecutionStatus.REJECTED)
            svc.repository.close()
    def test_broken_sqlite_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"bad.db"; p.write_bytes(b"not sqlite")
            with self.assertRaises(sqlite3.DatabaseError): WorkflowService(p)
    def test_timeout_terminal(self):
        with tempfile.TemporaryDirectory() as td:
            runner=custom_runner(Path(td)/"x.db",SlowDataQuality()); data={"price":1,"previous_price":1,"volume":0,"timestamp":datetime.now(UTC).isoformat()}
            out=asyncio.run(runner.run(self.definition(),data,event_id="e",correlation_id="c",market="x",symbol="x")); self.assertEqual(out.status,ExecutionStatus.TIMEOUT)
            self.assertEqual(runner._repository.get_execution(out.execution_id)["status"],"TIMEOUT"); runner._repository.close()
    def test_cancellation_terminal(self):
        async def scenario(runner):
            task=asyncio.create_task(runner.run(self.definition(),{},event_id="e",correlation_id="c",market="x",symbol="x")); await asyncio.sleep(.01); task.cancel(); return await task
        with tempfile.TemporaryDirectory() as td:
            runner=custom_runner(Path(td)/"x.db",SlowDataQuality()); out=asyncio.run(scenario(runner)); self.assertEqual(out.status,ExecutionStatus.CANCELLED); runner._repository.close()

if __name__ == "__main__": unittest.main()

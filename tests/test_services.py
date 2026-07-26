import tempfile, unittest
from datetime import UTC, datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from stimpy.config import StimpyConfig
from stimpy.observation_adapter import ObservationAdapter
from stimpy.observation_store import ObservationStore
from stimpy.memory_service import MemoryService
from stimpy.learning_service import LearningService
from stimpy.knowledge_graph import build_graph

class ServiceTests(unittest.TestCase):
    def event(self,i=1,topic="DECISION_CREATED",corr="c1"):
        return {"event_id":f"e{i}","correlation_id":corr,"topic":topic,"market":"crypto","symbol":"BTC","observed_at":datetime.now(UTC).isoformat(),"payload":{"decision":"BUY","api_token":"hidden"}}
    def test_append_duplicate_and_redaction(self):
        with tempfile.TemporaryDirectory() as td:
            s=ObservationStore(Path(td)/"x.db"); a=ObservationAdapter(s,StimpyConfig().observation_topics)
            self.assertTrue(a.observe_event(self.event())); self.assertFalse(a.observe_event(self.event())); self.assertEqual(s.list()[0]["payload"]["api_token"],"[REDACTED]"); self.assertTrue(s.foreign_keys_enabled)
            s.close()
    def test_allowlist_and_outage_isolation(self):
        with tempfile.TemporaryDirectory() as td:
            s=ObservationStore(Path(td)/"x.db"); a=ObservationAdapter(s,StimpyConfig().observation_topics)
            self.assertFalse(a.observe_event(self.event(topic="ORDER_CREATED"))); self.assertFalse(a.source_unavailable())
            s.close()
    def test_concurrent_duplicate_safe(self):
        with tempfile.TemporaryDirectory() as td:
            a=ObservationAdapter(ObservationStore(Path(td)/"x.db"),StimpyConfig().observation_topics)
            with ThreadPoolExecutor(max_workers=8) as pool: results=list(pool.map(lambda _:a.observe_event(self.event()),range(30)))
            self.assertEqual(sum(results),1)
            a.store.close()
    def test_memory_learning_and_graph(self):
        with tempfile.TemporaryDirectory() as td:
            s=ObservationStore(Path(td)/"x.db"); a=ObservationAdapter(s,StimpyConfig().observation_topics)
            a.observe_event(self.event(1,"BRAIN_DECISION_RECEIVED")); e=self.event(2,"DECISION_CREATED"); e["payload"]={"decision":"SELL"}; a.observe_event(e)
            snap=MemoryService(s).snapshot(); self.assertEqual(snap["contradictions"],1); self.assertEqual(LearningService(MemoryService(s)).analyze()["model_updates"],0)
            self.assertEqual(build_graph()["cluster"],"StimpyBrain")
            s.close()
    def test_no_active_integration_configuration(self):
        cfg=StimpyConfig(); self.assertEqual(cfg.mode,"observe"); self.assertFalse(hasattr(cfg,"broker_url")); self.assertFalse(hasattr(cfg,"telegram_token"))

if __name__ == "__main__": unittest.main()

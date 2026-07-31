import json,math,sqlite3,tempfile,unittest
from dataclasses import replace
from datetime import UTC,datetime
from pathlib import Path
from unittest.mock import patch
from stimpy.demo_reasoning_prototype import run_demo
from stimpy.evidence import EvidenceEngine
from stimpy.knowledge_graph import KnowledgeGraph
from stimpy.memory_service import Memory
from stimpy.models import KnowledgeStatus
from stimpy.observation_store import ObservationStore
from stimpy.observer import Observer
from stimpy.prototype import StimpyPrototypeService
from stimpy.reasoning import ReasoningEngine
from stimpy.self_critic import SelfCritic

GOOD={"symbol":"BTCUSDT","market":"crypto","decision":"LONG","confidence":.87,"outcome":"WIN","profit":7.2,"source":"test","timestamp":"2026-07-31T12:00:00+00:00"}

class ReasoningPrototypeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name); self.store=ObservationStore(self.root/"database"/"x.sqlite3",self.root); self.observer=Observer()
    def tearDown(self):
        try:self.store.close()
        except Exception:pass
        self.temp.cleanup()
    def test_valid_model_utc_and_stable_id(self):
        one=self.observer.receive(GOOD); two=self.observer.receive(dict(GOOD)); self.assertEqual(one.observation_id,two.observation_id); self.assertEqual(one.timestamp.tzinfo,UTC); self.assertEqual(one.decision,"LONG")
    def test_model_rejects_confidence_profit_direction_and_outcome(self):
        for key,value,error in (("confidence",1.1,ValueError),("confidence","high",TypeError),("profit",math.nan,ValueError),("profit",math.inf,ValueError),("decision","BUY",ValueError),("outcome","MAYBE",ValueError)):
            with self.subTest(key=key,value=value),self.assertRaises(error): self.observer.receive({**GOOD,key:value})
    def test_observer_missing_fields_and_does_not_mutate(self):
        payload=dict(GOOD); before=dict(payload); self.observer.receive(payload); self.assertEqual(payload,before)
        with self.assertRaises(ValueError): self.observer.receive({"symbol":"BTC"})
        with self.assertRaises(TypeError): self.observer.receive([])
    def test_memory_jsonl_duplicate_recent_and_timestamp(self):
        memory=Memory(self.store); observation=self.observer.receive(GOOD); self.assertTrue(memory.remember(observation)); self.assertFalse(memory.remember(observation)); self.assertTrue(memory.exists(observation.observation_id)); self.assertEqual(memory.load_recent(1),[observation])
        line=next((self.root/"observations").glob("*.jsonl")).read_text(encoding="utf-8").splitlines()[0]; item=json.loads(line); self.assertEqual(item["source_timestamp"],GOOD["timestamp"]); self.assertTrue((self.root/"database").is_dir())
    def test_incomplete_last_jsonl_line_and_write_error(self):
        path=self.root/"observations"/"broken.jsonl"; path.write_bytes(b'{"ok":1}\n{"partial":')
        valid,corrupt=self.store.validate_jsonl(path); self.assertEqual(valid,[{"ok":1}]); self.assertEqual(corrupt,[])
        with patch("pathlib.Path.open",side_effect=OSError("read only")),self.assertRaises(OSError): Memory(self.store).remember(self.observer.receive(GOOD))
    def test_evidence_rules_and_normalization(self):
        engine=EvidenceEngine(); win=engine.evaluate(self.observer.receive(GOOD)); self.assertEqual(win.score,7); self.assertEqual(win.normalized_score,1.0)
        loss=engine.evaluate(self.observer.receive({**GOOD,"outcome":"LOSS","profit":-4})); self.assertLess(loss.score,0); self.assertTrue(loss.contradicting_evidence)
        unknown=engine.evaluate(self.observer.receive({**GOOD,"outcome":"UNKNOWN","profit":0,"confidence":.5})); self.assertEqual(unknown.score,0); self.assertFalse(unknown.supporting_evidence)
    def test_reasoning_is_uncertain_noncausal_and_has_no_order(self):
        obs=self.observer.receive(GOOD); result=ReasoningEngine().think(obs,EvidenceEngine().evaluate(obs)); encoded=repr(result).lower()
        self.assertTrue(result.reasons); self.assertTrue(result.counterarguments); self.assertGreater(result.uncertainty,0); self.assertIn("no causal",result.conclusion.lower()); self.assertNotIn("order",encoded)
    def test_self_critic_cases(self):
        critic=SelfCritic(); bad=critic.analyse(self.observer.receive({**GOOD,"confidence":.95,"outcome":"LOSS","profit":-7})); self.assertEqual(bad.severity,"MEDIUM"); self.assertGreaterEqual(len(bad.issues),3)
        inconsistent=critic.analyse(self.observer.receive({**GOOD,"outcome":"WIN","profit":-1})); self.assertEqual(inconsistent.severity,"HIGH")
        normal=critic.analyse(self.observer.receive({**GOOD,"confidence":.7,"profit":1})); self.assertEqual(normal.issues,())
    def test_knowledge_is_sqlite_provisional_and_not_overwritten(self):
        service=StimpyPrototypeService(self.store); first=service.process(GOOD); second=service.process(GOOD)
        self.assertEqual(first.knowledge_entry.status,KnowledgeStatus.PROVISIONAL); self.assertFalse(second.stored); self.assertEqual(len(KnowledgeGraph(self.store).load_all()),1); self.assertEqual(first.knowledge_entry.created_at,second.knowledge_entry.created_at)
    def test_corrupt_sqlite_fails_closed(self):
        self.store.close(); broken=self.root/"database"/"broken.sqlite3"; broken.write_text("invalid",encoding="utf-8")
        with self.assertRaises(sqlite3.DatabaseError): ObservationStore(broken,self.root/"other")
    def test_complete_service_and_demo_are_local_only(self):
        result=StimpyPrototypeService(self.store).process(GOOD); self.assertTrue(result.stored); self.assertEqual(result.observation.source,"test")
        lines=[]; demo_root=self.root/"demo"; demo=run_demo(demo_root,lines.append); text="\n".join(lines).lower(); self.assertIn("simulated local demo",text); self.assertNotIn("pandorick",text); self.assertFalse(any(word in text for word in ("broker","telegram","create order"))); self.assertTrue(str(demo_root).startswith(str(self.root)))

if __name__=="__main__": unittest.main()

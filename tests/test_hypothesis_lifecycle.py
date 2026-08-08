import json,tempfile,unittest,urllib.error,urllib.request
from datetime import UTC,datetime
from pathlib import Path

from stimpy.api import ReadOnlyAPI,StimpyApiServer
from stimpy.hypothesis_engine import HypothesisEngine
from stimpy.hypothesis_lifecycle import HypothesisLifecycleService
from stimpy.knowledge_graph import build_graph
from stimpy.learning_service import LearningService
from stimpy.memory_service import MemoryService
from stimpy.models import HypothesisLifecycleAction,HypothesisStatus
from stimpy.observation_store import ObservationStore


class HypothesisLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name); self.path=self.root/"database"/"stimpy.sqlite3"; self.now=datetime(2026,8,8,14,tzinfo=UTC)
        self.store=ObservationStore(self.path,self.root); self.engine=HypothesisEngine(self.store,clock=lambda:self.now); self.service=HypothesisLifecycleService(self.store,clock=lambda:self.now)
        self.hypothesis=self.engine.create_hypothesis("A bounded research statement.","Should it remain active?",["market_data"])
    def tearDown(self):
        try:self.store.close()
        except Exception:pass
        self.temp.cleanup()
    def test_reject_is_atomic_persistent_and_idempotent(self):
        first=self.service.reject(self.hypothesis.hypothesis_id,"Evidence design is invalid.","reviewer"); second=self.service.reject(self.hypothesis.hypothesis_id,"Evidence design is invalid.","reviewer")
        self.assertEqual(first,second); self.assertEqual(first.action,HypothesisLifecycleAction.REJECT); self.assertEqual(first.from_status,HypothesisStatus.NEW); self.assertEqual(self.store.get_hypothesis(self.hypothesis.hypothesis_id).status,HypothesisStatus.REJECTED); self.assertEqual(self.store.count("hypothesis_lifecycle_events"),1)
        self.store.close(); self.store=ObservationStore(self.path,self.root); self.assertEqual(self.store.get_hypothesis_lifecycle_event(first.event_id),first); self.assertEqual(self.store.schema_version,10)
    def test_archive_preserves_prior_rejection_audit(self):
        rejected=self.service.reject(self.hypothesis.hypothesis_id,"Unsupported research design."); archived=self.service.archive(self.hypothesis.hypothesis_id,"Retain for historical review.")
        self.assertEqual(archived.from_status,HypothesisStatus.REJECTED); self.assertEqual(self.store.get_hypothesis(self.hypothesis.hypothesis_id).status,HypothesisStatus.ARCHIVED); events=self.store.list_hypothesis_lifecycle_events(self.hypothesis.hypothesis_id); self.assertEqual({item["event_id"] for item in events},{rejected.event_id,archived.event_id})
    def test_terminal_states_block_mutation_and_conflicting_repeats(self):
        self.service.reject(self.hypothesis.hypothesis_id,"Not testable.")
        with self.assertRaises(ValueError): self.service.reject(self.hypothesis.hypothesis_id,"Different reason.")
        with self.assertRaises(ValueError): self.engine.evaluate_hypothesis(self.hypothesis.hypothesis_id)
        self.service.archive(self.hypothesis.hypothesis_id,"Close review.")
        with self.assertRaises(ValueError): self.service.reject(self.hypothesis.hypothesis_id,"Cannot reopen.")
    def test_reason_actor_and_unknown_hypothesis_fail_closed(self):
        for value in ("", "token=secret"):
            with self.assertRaises(ValueError): self.service.reject(self.hypothesis.hypothesis_id,value)
        with self.assertRaises(ValueError): self.service.reject(self.hypothesis.hypothesis_id,"Valid reason","api_key=secret")
        with self.assertRaises(KeyError): self.service.archive("missing","Reason")
        self.assertEqual(self.store.count("hypothesis_lifecycle_events"),0); self.assertEqual(self.store.get_hypothesis(self.hypothesis.hypothesis_id).status,HypothesisStatus.NEW)
    def test_get_only_api_exposes_bounded_audit_history(self):
        event=self.service.reject(self.hypothesis.hypothesis_id,"Audit through projection."); memory=MemoryService(self.store); api=ReadOnlyAPI(self.store,memory,LearningService(memory),build_graph); server=StimpyApiServer(api,port=0); server.start()
        try:
            url=f"{server.url}/api/stimpy/hypotheses/{self.hypothesis.hypothesis_id}/lifecycle"; payload=json.loads(urllib.request.urlopen(url,timeout=2).read()); self.assertEqual(payload["items"][0]["event_id"],event.event_id); self.assertEqual(payload["total"],1)
            request=urllib.request.Request(url,data=b"{}",method="POST")
            with self.assertRaises(urllib.error.HTTPError) as caught: urllib.request.urlopen(request,timeout=2)
            self.assertEqual(caught.exception.code,405)
        finally:server.stop()


if __name__=="__main__": unittest.main()

import json,tempfile,unittest,urllib.request
from datetime import UTC,datetime,timedelta
from pathlib import Path

from stimpy.api import ReadOnlyAPI,StimpyApiServer
from stimpy.incubation_service import IncubationService
from stimpy.knowledge_graph import build_graph
from stimpy.learning_service import LearningService
from stimpy.memory_service import MemoryService
from stimpy.models import IncubationStatus
from stimpy.observation_store import ObservationStore
from stimpy.prototype import StimpyPrototypeService


INITIAL={"symbol":"BTCUSDT","market":"crypto","decision":"LONG","confidence":.87,"outcome":"WIN","profit":7.2,"source":"test","timestamp":"2026-08-01T10:00:00+00:00"}
FOLLOWUP={"symbol":"BTCUSDT","market":"crypto","decision":"SHORT","confidence":.55,"outcome":"LOSS","profit":-3.0,"source":"test","timestamp":"2026-08-01T11:00:00+00:00"}


class IncubationServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name); self.path=self.root/"database"/"stimpy.sqlite3"
        self.store=ObservationStore(self.path,self.root); self.now=datetime(2026,8,1,12,tzinfo=UTC); self.prototype=StimpyPrototypeService(self.store)
        self.initial=self.prototype.process(INITIAL); self.service=IncubationService(self.store,default_seconds=3600,max_retries=2,clock=lambda:self.now)
    def tearDown(self):
        try:self.store.close()
        except Exception:pass
        self.temp.cleanup()
    def create(self): return self.service.create(self.initial.observation.observation_id,"Should this conclusion survive new evidence?")
    def test_create_is_persistent_idempotent_and_incubating(self):
        first=self.create(); second=self.create(); self.assertEqual(first,second); self.assertEqual(first.status,IncubationStatus.INCUBATING); self.assertEqual(self.store.count("incubation_tasks"),1)
        self.store.close(); self.store=ObservationStore(self.path,self.root); self.service=IncubationService(self.store,clock=lambda:self.now); self.assertEqual(self.service.get(first.incubation_id),first); self.assertEqual(self.store.schema_version,11)
    def test_due_transition_is_explicit(self):
        task=self.create(); self.assertEqual(self.service.mark_ready(self.now),0); self.assertEqual(self.service.get(task.incubation_id).status,IncubationStatus.INCUBATING)
        self.assertEqual(self.service.mark_ready(task.reactivate_at),1); self.assertEqual(self.service.get(task.incubation_id).status,IncubationStatus.READY)
    def test_reactivation_requires_new_persisted_evidence(self):
        task=self.create(); followup=self.prototype.process(FOLLOWUP)
        with self.assertRaises(ValueError): self.service.reactivate(task.incubation_id,(followup.observation.observation_id,),followup.reasoning.reasoning_id,self.now)
        with self.assertRaises(ValueError): self.service.reactivate(task.incubation_id,(),self.initial.reasoning.reasoning_id,task.reactivate_at)
        with self.assertRaises(ValueError): self.service.reactivate(task.incubation_id,(self.initial.observation.observation_id,),self.initial.reasoning.reasoning_id,task.reactivate_at)
        with self.assertRaises(TypeError): self.service.reactivate(task.incubation_id,followup.observation.observation_id,followup.reasoning.reasoning_id,task.reactivate_at)
        self.assertEqual(self.service.get(task.incubation_id).status,IncubationStatus.READY)
    def test_reactivation_compares_and_preserves_both_analyses(self):
        task=self.create(); followup=self.prototype.process(FOLLOWUP)
        resolved=self.service.reactivate(task.incubation_id,(followup.observation.observation_id,),followup.reasoning.reasoning_id,task.reactivate_at)
        self.assertEqual(resolved.status,IncubationStatus.RESOLVED); self.assertEqual(resolved.initial_reasoning_id,self.initial.reasoning.reasoning_id); self.assertEqual(resolved.final_reasoning_id,followup.reasoning.reasoning_id); self.assertTrue(resolved.comparison.direction_changed); self.assertNotEqual(resolved.comparison.score_delta,0); self.assertIn("changed",resolved.conclusion.lower())
        self.assertIsNotNone(self.store.get_reasoning(resolved.initial_reasoning_id)); self.assertIsNotNone(self.store.get_reasoning(resolved.final_reasoning_id))
        self.assertEqual(self.service.reactivate(task.incubation_id,(followup.observation.observation_id,),followup.reasoning.reasoning_id,task.reactivate_at),resolved)
    def test_failure_retries_never_leave_running_state(self):
        task=self.create(); self.service.mark_ready(task.reactivate_at); once=self.service.record_failure(task.incubation_id,TimeoutError("secret detail"))
        self.assertEqual(once.status,IncubationStatus.READY); self.assertEqual(once.last_error,"TimeoutError"); twice=self.service.record_failure(task.incubation_id,RuntimeError("again")); self.assertEqual(twice.status,IncubationStatus.FAILED); self.assertEqual(twice.failure_count,2); self.assertNotIn(twice.status.value,{"RUNNING","INCUBATING"})
    def test_cancel_is_idempotent(self):
        task=self.create(); cancelled=self.service.cancel(task.incubation_id); self.assertEqual(cancelled.status,IncubationStatus.CANCELLED); self.assertEqual(self.service.cancel(task.incubation_id),cancelled)
        with self.assertRaises(ValueError): self.service.reactivate(task.incubation_id,(),"missing",task.reactivate_at)
    def test_get_only_api_lists_bounded_tasks(self):
        task=self.create(); memory=MemoryService(self.store); api=ReadOnlyAPI(self.store,memory,LearningService(memory),build_graph); server=StimpyApiServer(api,port=0); server.start()
        try:
            payload=json.loads(urllib.request.urlopen(server.url+"/api/stimpy/incubation?status=INCUBATING&limit=1",timeout=2).read()); self.assertEqual(payload["total"],1); self.assertEqual(payload["items"][0]["incubation_id"],task.incubation_id); self.assertEqual(payload["items"][0]["status"],"INCUBATING")
        finally: server.stop()


if __name__=="__main__": unittest.main()

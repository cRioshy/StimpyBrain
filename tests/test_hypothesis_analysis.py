import json,tempfile,unittest,urllib.request
from datetime import UTC,datetime,timedelta
from pathlib import Path

from stimpy.api import ReadOnlyAPI,StimpyApiServer
from stimpy.hypothesis_analysis import HypothesisAnalysisService
from stimpy.hypothesis_engine import HypothesisEngine
from stimpy.knowledge_graph import build_graph
from stimpy.learning_service import LearningService
from stimpy.memory_service import MemoryService
from stimpy.models import HypothesisStatus,IncubationStatus
from stimpy.observation_store import ObservationStore
from stimpy.prototype import StimpyPrototypeService


class HypothesisAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.path=self.root/"database"/"stimpy.sqlite3";self.now=datetime(2026,8,8,10,tzinfo=UTC)
        self.store=ObservationStore(self.path,self.root);self.prototype=StimpyPrototypeService(self.store);self.engine=HypothesisEngine(self.store,min_provisional_cases=3,min_supported_cases=5,clock=lambda:self.now);self.analysis=HypothesisAnalysisService(self.store,self.engine,default_seconds=60,max_retries=2,clock=lambda:self.now)
        self.hypothesis=self.engine.create_hypothesis("Rising hashrate may precede BTC returns.","Does BTC rise after hashrate increases?",["network_hashrate","future_return"])
    def tearDown(self):
        try:self.store.close()
        except Exception:pass
        self.temp.cleanup()
    def add(self,number,direction="SUPPORTING",source="market"):
        timestamp=(datetime(2026,8,1,tzinfo=UTC)+timedelta(hours=number)).isoformat();payload={"observation_id":f"analysis-{number}","symbol":"BTCUSDT","market":"crypto","decision":"LONG","confidence":.7,"outcome":"WIN","profit":number+1,"source":"test","timestamp":timestamp}
        observation=self.prototype.process(payload).observation
        return self.engine.add_evidence(self.hypothesis.hypothesis_id,source,direction,.8,.8,f"case {number}",[observation.observation_id])
    def test_reasoning_and_critic_are_complete_persistent_and_idempotent(self):
        self.add(0);first,critic=self.analysis.analyse(self.hypothesis.hypothesis_id);second,second_critic=self.analysis.analyse(self.hypothesis.hypothesis_id)
        self.assertEqual(first,second);self.assertEqual(critic,second_critic);self.assertTrue(first.reasons);self.assertTrue(first.counterarguments);self.assertTrue(first.missing_information);self.assertTrue(first.alternative_explanations);self.assertIn("non-causal",first.conclusion);self.assertTrue(critic.bias_warnings);self.assertIn("sample size",critic.issues[0]);self.assertEqual(self.store.count("hypothesis_reasoning"),1);self.assertEqual(self.store.count("hypothesis_critics"),1)
        self.store.close();self.store=ObservationStore(self.path,self.root);self.assertEqual(self.store.get_hypothesis_reasoning(first.reasoning_id),first);self.assertEqual(self.store.schema_version,9)
    def test_critic_flags_causal_language_and_missing_counterexamples(self):
        causal=self.engine.create_hypothesis("Hashrate causes BTC to rise.","Does it?",["hashrate","price"]);self.hypothesis=causal;self.add(1);reasoning,critic=self.analysis.analyse(causal.hypothesis_id)
        self.assertEqual(critic.severity.value,"HIGH");self.assertTrue(any("caus" in item for item in critic.issues));self.assertTrue(any("counterexample" in item for item in critic.issues));self.assertNotIn("order",repr(reasoning).lower())
    def test_incubation_requires_evidence_and_is_idempotent(self):
        with self.assertRaises(ValueError): self.analysis.create_incubation(self.hypothesis.hypothesis_id,"Wait for evidence")
        self.add(0);task=self.analysis.create_incubation(self.hypothesis.hypothesis_id,"Wait for evidence");again=self.analysis.create_incubation(self.hypothesis.hypothesis_id,"Wait for evidence")
        self.assertEqual(task,again);self.assertEqual(task.status,IncubationStatus.INCUBATING);self.assertEqual(self.store.get_hypothesis(self.hypothesis.hypothesis_id).status,HypothesisStatus.INCUBATING)
    def test_reactivation_requires_due_time_and_new_independent_evidence(self):
        self.add(0);task=self.analysis.create_incubation(self.hypothesis.hypothesis_id,"Review later")
        with self.assertRaises(ValueError): self.analysis.reactivate(task.incubation_id,self.now)
        due=task.reactivate_at;self.assertEqual(self.analysis.mark_ready(due),1)
        with self.assertRaises(ValueError): self.analysis.reactivate(task.incubation_id,due)
        self.now=due+timedelta(seconds=1);new=self.add(1,"CONTRADICTING");resolved=self.analysis.reactivate(task.incubation_id,self.now)
        self.assertEqual(resolved.status,IncubationStatus.RESOLVED);self.assertEqual(resolved.new_evidence_ids,(new.evidence_id,));self.assertTrue(resolved.final_evaluation_id);self.assertTrue(resolved.final_reasoning_id);self.assertEqual(resolved.comparison.independent_case_delta,1);self.assertEqual(self.analysis.reactivate(task.incubation_id,self.now),resolved)
    def test_first_analysis_survives_reactivation_and_restart(self):
        self.add(0);task=self.analysis.create_incubation(self.hypothesis.hypothesis_id,"Preserve first");initial_reasoning=self.store.get_hypothesis_reasoning(task.initial_reasoning_id);self.now=task.reactivate_at;self.add(1);resolved=self.analysis.reactivate(task.incubation_id,self.now)
        self.assertEqual(self.store.get_hypothesis_reasoning(initial_reasoning.reasoning_id),initial_reasoning);self.assertNotEqual(resolved.initial_reasoning_id,resolved.final_reasoning_id)
        self.store.close();self.store=ObservationStore(self.path,self.root);self.assertEqual(self.store.get_hypothesis_incubation(task.incubation_id),resolved)
    def test_get_only_api_projects_reasoning_critic_and_incubation(self):
        self.add(0);reasoning,critic=self.analysis.analyse(self.hypothesis.hypothesis_id);task=self.analysis.create_incubation(self.hypothesis.hypothesis_id,"API task");memory=MemoryService(self.store);api=ReadOnlyAPI(self.store,memory,LearningService(memory),build_graph);server=StimpyApiServer(api,port=0);server.start()
        try:
            base=server.url+"/api/stimpy/hypotheses/"+self.hypothesis.hypothesis_id
            projected_reasoning=json.loads(urllib.request.urlopen(base+"/reasoning",timeout=2).read());projected_critic=json.loads(urllib.request.urlopen(base+"/critic",timeout=2).read());incubations=json.loads(urllib.request.urlopen(server.url+"/api/stimpy/hypothesis-incubations?status=INCUBATING",timeout=2).read())
            self.assertEqual(projected_reasoning["reasoning_id"],reasoning.reasoning_id);self.assertEqual(projected_critic["critic_id"],critic.critic_id);self.assertEqual(incubations["items"][0]["incubation_id"],task.incubation_id)
            encoded=json.dumps((projected_reasoning,projected_critic,incubations)).lower();self.assertNotIn("broker",encoded);self.assertNotIn("telegram",encoded);self.assertNotIn("create_order",encoded)
        finally:server.stop()


if __name__=="__main__":unittest.main()

import json,math,tempfile,unittest,urllib.request
from dataclasses import replace
from datetime import UTC,datetime
from pathlib import Path

from stimpy.api import ReadOnlyAPI,StimpyApiServer
from stimpy.knowledge_graph import build_graph
from stimpy.learning_service import LearningService
from stimpy.memory_service import MemoryService
from stimpy.models import PatternStatus
from stimpy.observation_store import ObservationStore
from stimpy.pattern_learning import PatternLearningService
from stimpy.prototype import StimpyPrototypeService


class PatternLearningTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name); self.path=self.root/"database"/"stimpy.sqlite3"
        self.store=ObservationStore(self.path,self.root); self.prototype=StimpyPrototypeService(self.store); self.now=datetime(2026,8,1,20,tzinfo=UTC)
        self.service=PatternLearningService(self.store,min_cases=3,supported_min_cases=4,max_provisional_confidence=.70,clock=lambda:self.now)
    def tearDown(self):
        try:self.store.close()
        except Exception:pass
        self.temp.cleanup()
    def case(self,number,outcome="WIN",regime="TRENDING",decision="LONG"):
        profit=number+1 if outcome=="WIN" else (-number-1 if outcome=="LOSS" else 0)
        payload={"observation_id":f"case-{number}-{outcome}-{regime}-{decision}","symbol":"BTCUSDT","market":"crypto","decision":decision,"confidence":.8,"outcome":outcome,"profit":profit,"source":"test","market_regime":regime,"timestamp":f"2026-08-01T{10+number:02d}:00:00+00:00"}
        return self.prototype.process(payload).observation.observation_id
    def test_grouping_is_stable_idempotent_and_persistent(self):
        ids=[self.case(0),self.case(1)]
        first=self.service.learn(ids)[0]; second=self.service.learn(ids)[0]
        self.assertEqual(first.pattern_id,second.pattern_id); self.assertEqual(second.observed_cases,2); self.assertEqual(self.store.count("pattern_cases"),2); self.assertEqual(first.status,PatternStatus.OBSERVED)
        self.store.close(); self.store=ObservationStore(self.path,self.root); self.assertEqual(self.store.get_pattern(first.pattern_id).observed_cases,2); self.assertEqual(self.store.schema_version,9)
    def test_pattern_model_rejects_invalid_counts_and_confidence(self):
        pattern=self.service.learn([self.case(0)])[0]
        with self.assertRaises(ValueError): replace(pattern,observed_cases=2)
        with self.assertRaises(ValueError): replace(pattern,confidence=math.nan)
        with self.assertRaises(ValueError): replace(pattern,confidence=math.inf)
    def test_minimum_cases_and_confidence_cap(self):
        pattern=self.service.learn([self.case(0),self.case(1),self.case(2)])[0]
        self.assertEqual(pattern.status,PatternStatus.PROVISIONAL); self.assertLessEqual(pattern.confidence,.70)
        supported=self.service.learn([self.case(3)])[0]; self.assertEqual(supported.status,PatternStatus.SUPPORTED); self.assertLessEqual(supported.confidence,.90)
    def test_negative_outcomes_are_retained_as_contradictions(self):
        pattern=self.service.learn([self.case(0,"WIN"),self.case(1,"LOSS"),self.case(2,"LOSS")])[0]
        self.assertEqual(pattern.positive_cases,1); self.assertEqual(pattern.negative_cases,2); self.assertEqual(pattern.contradiction_count,2); self.assertEqual(pattern.status,PatternStatus.CONTRADICTED)
    def test_unresolved_cases_do_not_count_as_positive(self):
        pattern=self.service.learn([self.case(0,"OPEN"),self.case(1,"UNKNOWN"),self.case(2,"WIN")])[0]
        self.assertEqual(pattern.unresolved_cases,2); self.assertEqual(pattern.positive_cases,1); self.assertEqual(pattern.evidence_count,3); self.assertLess(pattern.confidence,.70)
    def test_market_regime_and_decision_split_groups(self):
        ids=[self.case(0,"WIN","TRENDING","LONG"),self.case(1,"WIN","RANGING","LONG"),self.case(2,"WIN","TRENDING","SHORT")]
        patterns=self.service.learn(ids); self.assertEqual(len(patterns),3); self.assertEqual({p.conditions["market_regime"] for p in patterns},{"TRENDING","RANGING"}); self.assertEqual(self.store.count("patterns"),3)
    def test_persisted_evidence_is_required(self):
        observation=self.prototype.observer.receive({"observation_id":"only-observation","symbol":"ETHUSD","market":"crypto","decision":"HOLD","confidence":.4,"outcome":"OPEN","profit":0,"source":"test"})
        self.store.append(observation)
        with self.assertRaises(ValueError): self.service.learn([observation.observation_id])
    def test_get_only_api_is_bounded_and_has_no_strategy_side_effect(self):
        pattern=self.service.learn([self.case(0),self.case(1),self.case(2)])[0]
        memory=MemoryService(self.store); api=ReadOnlyAPI(self.store,memory,LearningService(memory),build_graph); server=StimpyApiServer(api,port=0); server.start()
        try:
            payload=json.loads(urllib.request.urlopen(server.url+"/api/stimpy/patterns?status=PROVISIONAL&limit=1",timeout=2).read())
            self.assertEqual(payload["total"],1); self.assertEqual(payload["items"][0]["pattern_id"],pattern.pattern_id); self.assertEqual(payload["model_updates"],0); self.assertEqual(payload["causal_claims"],0)
            encoded=json.dumps(payload).lower(); self.assertNotIn("order",encoded); self.assertNotIn("broker",encoded); self.assertNotIn("strategy_change",encoded)
        finally: server.stop()


if __name__=="__main__": unittest.main()

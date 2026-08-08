import json,math,tempfile,unittest,urllib.error,urllib.request
from dataclasses import replace
from datetime import UTC,datetime,timedelta
from pathlib import Path

from stimpy.api import ReadOnlyAPI,StimpyApiServer
from stimpy.hypothesis_engine import HypothesisEngine
from stimpy.knowledge_graph import build_graph
from stimpy.learning_service import LearningService
from stimpy.memory_service import MemoryService
from stimpy.models import HypothesisStatus
from stimpy.observation_store import ObservationStore
from stimpy.prototype import StimpyPrototypeService


class HypothesisFoundationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name); self.path=self.root/"database"/"stimpy.sqlite3"
        self.store=ObservationStore(self.path,self.root); self.prototype=StimpyPrototypeService(self.store); self.now=datetime(2026,8,8,8,tzinfo=UTC)
        self.engine=HypothesisEngine(self.store,min_investigating_cases=2,min_provisional_cases=3,min_supported_cases=4,min_supported_ratio=.70,max_contradicted_ratio=.30,clock=lambda:self.now)
    def tearDown(self):
        try:self.store.close()
        except Exception:pass
        self.temp.cleanup()
    def create(self):
        return self.engine.create_hypothesis("Rising hashrate may precede positive BTC returns.","Does BTC rise more often after hashrate increases?",["network_hashrate","btc_price","future_return"])
    def observation(self,number):
        timestamp=(datetime(2026,8,1,tzinfo=UTC)+timedelta(hours=number)).isoformat()
        payload={"observation_id":f"hyp-case-{number}","symbol":"BTCUSDT","market":"crypto","decision":"LONG","confidence":.75,"outcome":"WIN","profit":number+1,"source":"test","timestamp":timestamp}
        return self.prototype.process(payload).observation.observation_id
    def evidence(self,hypothesis,number,direction="SUPPORTING",source="market"):
        return self.engine.add_evidence(hypothesis.hypothesis_id,source,direction,.8,.9,f"Independent case {number}",[self.observation(number)])
    def test_create_is_stable_idempotent_bounded_and_persistent(self):
        first=self.create(); second=self.create(); self.assertEqual(first,second); self.assertEqual(first.status,HypothesisStatus.NEW); self.assertEqual(self.store.count("hypotheses"),1)
        similar=self.engine.create_hypothesis(first.statement+" Possibly.",first.question,first.required_data); self.assertNotEqual(first.hypothesis_id,similar.hypothesis_id)
        with self.assertRaises(ValueError): self.engine.create_hypothesis("","Question?",["price"])
        with self.assertRaises(ValueError): self.engine.create_hypothesis("token=secret","Question?",["price"])
        self.store.close(); self.store=ObservationStore(self.path,self.root); self.assertEqual(self.store.get_hypothesis(first.hypothesis_id),first); self.assertEqual(self.store.schema_version,7)
    def test_model_rejects_invalid_confidence_counts_and_schema(self):
        hypothesis=self.create()
        with self.assertRaises(ValueError): replace(hypothesis,confidence=math.nan)
        with self.assertRaises(ValueError): replace(hypothesis,evidence_count=0,contradiction_count=1)
        with self.assertRaises(ValueError): replace(hypothesis,schema_version=2)
    def test_evidence_directions_validation_and_idempotency(self):
        hypothesis=self.create(); supporting=self.evidence(hypothesis,0)
        self.assertEqual(self.evidence(hypothesis,0),supporting)
        same_origin=self.engine.add_evidence(hypothesis.hypothesis_id,"other","CONTRADICTING",.2,.5,"Derived again",[supporting.source_observation_ids[0]])
        self.assertEqual(same_origin.evidence_id,supporting.evidence_id); self.assertEqual(self.store.count("hypothesis_evidence"),1)
        self.evidence(hypothesis,1,"CONTRADICTING"); self.evidence(hypothesis,2,"NEUTRAL"); self.assertEqual(self.store.count("hypothesis_evidence"),3)
        for value in (math.nan,math.inf,-.1,1.1):
            with self.subTest(value=value),self.assertRaises(ValueError): self.engine.add_evidence(hypothesis.hypothesis_id,"x","SUPPORTING",value,.5,"bad",[self.observation(10+len(str(value)))])
    def test_unknown_observation_and_foreign_key_fail_closed(self):
        hypothesis=self.create()
        with self.assertRaises(KeyError): self.engine.add_evidence(hypothesis.hypothesis_id,"x","SUPPORTING",.5,.5,"missing",["missing"])
        with self.assertRaises(KeyError): self.engine.add_evidence("missing","x","SUPPORTING",.5,.5,"missing",[self.observation(0)])
        with self.assertRaises(ValueError): self.engine.add_evidence(hypothesis.hypothesis_id,"x","SUPPORTING",.5,.5,"mixed origins",[self.observation(1),self.observation(2)])
        self.assertEqual(self.store._db.execute("PRAGMA foreign_key_check").fetchall(),[])
    def test_zero_and_three_cases_never_supported(self):
        hypothesis=self.create(); empty=self.engine.evaluate_hypothesis(hypothesis.hypothesis_id); self.assertEqual(empty.status,HypothesisStatus.NEW); self.assertEqual(empty.confidence,0); self.assertEqual(empty.evidence_ratio,0)
        for number in range(3): self.evidence(hypothesis,number)
        evaluation=self.engine.evaluate_hypothesis(hypothesis.hypothesis_id); self.assertEqual(evaluation.status,HypothesisStatus.PROVISIONAL); self.assertNotEqual(evaluation.evidence_ratio,evaluation.confidence); self.assertLessEqual(evaluation.confidence,.70)
    def test_supported_requires_count_quality_ratio_and_source_diversity(self):
        hypothesis=self.create()
        for number in range(4): self.evidence(hypothesis,number,source="market" if number%2==0 else "mining")
        evaluation=self.engine.evaluate_hypothesis(hypothesis.hypothesis_id); self.assertEqual(evaluation.status,HypothesisStatus.SUPPORTED); self.assertEqual(evaluation.supporting_count,4); self.assertEqual(evaluation.source_count,2); self.assertLessEqual(evaluation.confidence,.90); self.assertIn("not proven",evaluation.explanation)
    def test_contradictions_and_neutral_cases_are_retained(self):
        hypothesis=self.create(); self.evidence(hypothesis,0,"SUPPORTING"); self.evidence(hypothesis,1,"CONTRADICTING"); self.evidence(hypothesis,2,"CONTRADICTING"); self.evidence(hypothesis,3,"CONTRADICTING"); self.evidence(hypothesis,4,"NEUTRAL")
        evaluation=self.engine.evaluate_hypothesis(hypothesis.hypothesis_id); self.assertEqual(evaluation.status,HypothesisStatus.CONTRADICTED); self.assertEqual(evaluation.contradicting_count,3); self.assertEqual(evaluation.neutral_count,1); self.assertEqual(self.store.count_hypothesis_evidence(hypothesis.hypothesis_id),5)
        updated=self.store.get_hypothesis(hypothesis.hypothesis_id); self.assertEqual(updated.contradiction_count,3); self.assertEqual(updated.neutral_count,1)
    def test_evaluation_is_idempotent_for_same_evidence_set(self):
        hypothesis=self.create(); self.evidence(hypothesis,0)
        first=self.engine.evaluate_hypothesis(hypothesis.hypothesis_id); self.now+=timedelta(hours=1); second=self.engine.evaluate_hypothesis(hypothesis.hypothesis_id)
        self.assertEqual(first,second); self.assertEqual(self.store.count("hypothesis_evaluations"),1); self.assertEqual(self.store.get_hypothesis(hypothesis.hypothesis_id).last_evaluated_at,first.evaluated_at)
    def test_get_only_api_lists_detail_evidence_and_evaluation(self):
        hypothesis=self.create(); self.evidence(hypothesis,0); evaluation=self.engine.evaluate_hypothesis(hypothesis.hypothesis_id)
        memory=MemoryService(self.store); api=ReadOnlyAPI(self.store,memory,LearningService(memory),build_graph); server=StimpyApiServer(api,port=0); server.start()
        try:
            base=server.url+"/api/stimpy/hypotheses"
            listing=json.loads(urllib.request.urlopen(base+"?status=INVESTIGATING&limit=1",timeout=2).read()); self.assertEqual(listing["total"],1); self.assertEqual(listing["causal_claims"],0)
            detail=json.loads(urllib.request.urlopen(base+"/"+hypothesis.hypothesis_id,timeout=2).read()); self.assertEqual(detail["hypothesis_id"],hypothesis.hypothesis_id)
            evidence=json.loads(urllib.request.urlopen(base+"/"+hypothesis.hypothesis_id+"/evidence",timeout=2).read()); self.assertEqual(evidence["total"],1)
            projected=json.loads(urllib.request.urlopen(base+"/"+hypothesis.hypothesis_id+"/evaluation",timeout=2).read()); self.assertEqual(projected["evaluation_id"],evaluation.evaluation_id)
            with self.assertRaises(urllib.error.HTTPError) as missing: urllib.request.urlopen(base+"/missing",timeout=2)
            self.assertEqual(missing.exception.code,404)
            with self.assertRaises(urllib.error.HTTPError) as write: urllib.request.urlopen(urllib.request.Request(base,method="POST"),timeout=2)
            self.assertEqual(write.exception.code,405)
            encoded=json.dumps((listing,detail,evidence,projected)).lower(); self.assertNotIn("broker",encoded); self.assertNotIn("telegram",encoded); self.assertNotIn("create_order",encoded)
        finally: server.stop()


if __name__=="__main__": unittest.main()

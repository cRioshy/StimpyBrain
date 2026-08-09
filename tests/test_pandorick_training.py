import json,tempfile,unittest,urllib.request,zipfile
from datetime import UTC,datetime,timedelta
from pathlib import Path
from stimpy.api import ReadOnlyAPI,StimpyApiServer
from stimpy.knowledge_graph import build_graph
from stimpy.learning_service import LearningService
from stimpy.memory_service import MemoryService
from stimpy.observation_store import ObservationStore
from stimpy.pandorick_training import PandorickTrainingService

class PandorickTrainingTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.store=ObservationStore(self.root/"db.sqlite3",self.root);self.service=PandorickTrainingService(self.store,clock=lambda:datetime(2026,8,8,tzinfo=UTC))
    def tearDown(self):self.store.close();self.temp.cleanup()
    def archive(self):
        path=self.root/"training.zip";decisions=[];outcomes=[];start=datetime(2026,1,1,tzinfo=UTC)
        for i in range(20):
            did=f"decision:{i}";symbol=("BTCUSDT","ETHUSDT","XRPUSDT")[i%3];decision={"event_type":"DECISION_CREATED","created_at":(start+timedelta(hours=i)).isoformat(),"payload":{"decision_id":did,"symbol":symbol,"direction":"LONG","confidence":50+i,"price_status":"ok","price_source":"test","analysis_close":100+i,"indicators":{"volatility":.005*(i%8),"volume_ratio":.6+.1*(i%10),"sma_20":99},"facts":{"trend":{"value":"UP" if i%2 else "DOWN"}}}};decisions.append(json.dumps(decision))
            closed={"record_type":"SIMULATED_TRADE_CLOSED","timestamp":(start+timedelta(hours=i,minutes=30)).isoformat(),"payload":{"decision_id":did,"signal_id":f"signal:{i}","symbol":symbol,"direction":"LONG","result_type":("WIN","LOSS","BREAKEVEN")[i%3],"gross_profit_percent":1 if i%3==0 else -1 if i%3==1 else 0}};outcomes.append(json.dumps(closed))
        decisions.append(json.dumps({"created_at":start.isoformat(),"payload":{"decision_id":"bad","symbol":"BTCUSDT","price_status":"unavailable"}}))
        with zipfile.ZipFile(path,"w") as z:z.writestr("Train/platform_decisions.jsonl","\n".join(decisions));z.writestr("Train/trade_outcomes.jsonl","\n".join(outcomes))
        return path
    def test_analysis_is_filtered_split_persistent_and_idempotent(self):
        first=self.service.analyse_archive(self.archive());second=self.service.analyse_archive(self.archive());self.assertEqual(first,second);self.assertEqual(first["decision_count"],20);self.assertEqual(first["linked_case_count"],20);self.assertEqual(self.store.count("pandorick_training_runs"),1);self.assertEqual(self.store.count("pandorick_training_cases"),20);self.assertGreater(self.store.count("pandorick_training_metrics"),5);self.assertEqual(self.store.schema_version,12)
    def test_get_only_metrics_projection(self):
        run=self.service.analyse_archive(self.archive());memory=MemoryService(self.store);server=StimpyApiServer(ReadOnlyAPI(self.store,memory,LearningService(memory),build_graph),port=0);server.start()
        try:
            runs=json.loads(urllib.request.urlopen(server.url+"/api/stimpy/training-runs",timeout=2).read());metrics=json.loads(urllib.request.urlopen(server.url+f"/api/stimpy/training-runs/{run['run_id']}/metrics?hypothesis_key=confidence_calibration&split=TEST",timeout=2).read());self.assertEqual(runs["items"][0]["linked_case_count"],20);self.assertTrue(metrics["items"]);self.assertTrue(all(m["split"]=="TEST" for m in metrics["items"]))
        finally:server.stop()

import csv,json,tempfile,unittest,urllib.request
from datetime import UTC,datetime,timedelta
from pathlib import Path
from stimpy.api import ReadOnlyAPI,StimpyApiServer
from stimpy.knowledge_graph import build_graph
from stimpy.learning_service import LearningService
from stimpy.memory_service import MemoryService
from stimpy.observation_store import ObservationStore
from stimpy.offline_replay import OfflineReplayService

class OfflineReplayTests(unittest.TestCase):
    def setUp(self): self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.store=ObservationStore(self.root/"db.sqlite3",self.root);self.service=OfflineReplayService(self.store,clock=lambda:datetime(2026,8,8,tzinfo=UTC))
    def tearDown(self): self.store.close();self.temp.cleanup()
    def csv(self,reverse=False):
        path=self.root/"btc.csv";rows=[];start=datetime(2025,1,1,tzinfo=UTC)
        for i in range(120):
            close=100+i*.4+(3 if i%15==0 else 0);rows.append([start+timedelta(minutes=15*i),close-.2,close+.5,close-.5,close,100+(i%15)*20])
        if reverse: rows[40],rows[41]=rows[41],rows[40]
        with path.open("w",newline="",encoding="utf-8") as f:
            writer=csv.writer(f);writer.writerow(["timestamp","open","high","low","close","volume"]);writer.writerows(rows)
        return path
    def test_replay_is_persistent_idempotent_and_split_without_boundary_leakage(self):
        first=self.service.run_csv(self.csv());second=self.service.run_csv(self.csv());self.assertEqual(first,second);self.assertEqual(self.store.count("replay_runs"),1);self.assertGreater(first["case_count"],0);cases=self.store.list_replay_cases(first["run_id"],1000,0);self.assertTrue({c["split"] for c in cases}.issubset({"TRAIN","VALIDATION","TEST"}));self.assertEqual(self.store.schema_version,12)
    def test_invalid_chronology_fails_closed(self):
        with self.assertRaises(ValueError):self.service.run_csv(self.csv(True))
        self.assertEqual(self.store.count("replay_runs"),0)
    def test_get_only_api_projects_runs_and_cases(self):
        run=self.service.run_csv(self.csv());memory=MemoryService(self.store);server=StimpyApiServer(ReadOnlyAPI(self.store,memory,LearningService(memory),build_graph),port=0);server.start()
        try:
            runs=json.loads(urllib.request.urlopen(server.url+"/api/stimpy/replay-runs",timeout=2).read());cases=json.loads(urllib.request.urlopen(server.url+f"/api/stimpy/replay-runs/{run['run_id']}/cases?split=TRAIN",timeout=2).read());self.assertEqual(runs["items"][0]["run_id"],run["run_id"]);self.assertTrue(all(c["split"]=="TRAIN" for c in cases["items"]))
        finally:server.stop()

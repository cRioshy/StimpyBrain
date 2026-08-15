import json,tempfile,unittest,urllib.error,urllib.request
from dataclasses import replace
from datetime import UTC,datetime,timedelta
from pathlib import Path
from stimpy.api import ReadOnlyAPI,StimpyApiServer
from stimpy.app import build_app
from stimpy.config import StimpyConfig
from stimpy.knowledge_graph import build_graph
from stimpy.learning_service import LearningService
from stimpy.memory_service import MemoryService
from stimpy.observation_store import ObservationStore
from stimpy.shitzo.lab import ShitzoDisabledError,ShitzoLab
from stimpy.shitzo.models import MarketTick
from stimpy.shitzo.repository import ShitzoRepository


class ShitzoLabApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.db=self.root/"database"/"stimpy.sqlite3";self.store=ObservationStore(self.db,self.root)
        self.repo=ShitzoRepository(self.db);base=StimpyConfig.from_env();self.config=replace(base,shitzo_enabled=True,database_file=self.db,data_dir=self.root);self.lab=ShitzoLab(self.repo,self.config);self.now=datetime(2026,1,1,tzinfo=UTC)
    def tearDown(self):
        if hasattr(self,"server"): self.server.stop()
        self.repo.close();self.store.close();self.tmp.cleanup()
    def tick(self,index,price=None): return MarketTick("BTC-USD",price or 100+index,self.now+timedelta(minutes=index),"fixture",f"tick-{index}")
    def test_explicit_bounded_lab_flow_and_stop_preserves_positions(self):
        run=self.lab.start("run-s4",self.now);self.assertEqual("run-s4",run);self.assertEqual(3,self.repo.count("shitzo_accounts",run))
        for i in range(19): result=self.lab.process_tick(self.tick(i),self.tick(i).timestamp);self.assertIsNone(result["snapshot"])
        result=self.lab.process_tick(self.tick(19),self.tick(19).timestamp);self.assertEqual(3,len(result["decisions"]));self.assertGreater(len(result["opened"]),0)
        open_before=self.repo.count("shitzo_positions",run);self.assertTrue(self.lab.stop(self.now+timedelta(minutes=20)));self.assertFalse(self.lab.active);self.assertEqual(open_before,self.repo.count("shitzo_positions",run));self.assertEqual("STOPPED",self.repo.get_run(run)["status"])
    def test_disabled_lab_and_unstarted_processing_fail_closed(self):
        disabled=ShitzoLab(self.repo,replace(self.config,shitzo_enabled=False))
        with self.assertRaises(ShitzoDisabledError): disabled.start("disabled",self.now)
        with self.assertRaises(RuntimeError): self.lab.process_tick(self.tick(0))
        self.assertEqual(0,self.repo.count("shitzo_lab_runs"))
    def test_composition_does_not_start_shitzo(self):
        other=self.root/"composed";config=replace(StimpyConfig.from_env(),shitzo_enabled=False,data_dir=other,database_file=other/"database"/"stimpy.sqlite3",api_port=0)
        app=build_app(config)
        try:
            self.assertFalse(app["shitzo_lab"].active);self.assertEqual(0,app["shitzo_repository"].count("shitzo_lab_runs"));self.assertFalse(app["api"].shitzo_status()["active"])
        finally:
            app["server"]._server.server_close();app["workflow"].repository.close();app["shitzo_repository"].close();app["store"].close()
    def test_get_only_api_projects_status_accounts_positions_decisions_and_trades(self):
        run=self.lab.start("run-api",self.now)
        for i in range(20): self.lab.process_tick(self.tick(i),self.tick(i).timestamp)
        self.lab.process_tick(self.tick(20,121),self.now+timedelta(minutes=20))
        memory=MemoryService(self.store);api=ReadOnlyAPI(self.store,memory,LearningService(memory),build_graph,None,self.lab,self.repo);self.server=StimpyApiServer(api,port=0);self.server.start()
        for endpoint in ("status","traders","accounts","positions","decisions","trades"):
            response=urllib.request.urlopen(f"{self.server.url}/api/stimpy/shitzo/{endpoint}?run_id={run}&limit=10",timeout=2);self.assertEqual(200,response.status);payload=json.load(response);self.assertIsInstance(payload,dict)
        open_payload=json.load(urllib.request.urlopen(f"{self.server.url}/api/stimpy/shitzo/positions?run_id={run}&status=OPEN",timeout=2));self.assertEqual(len(open_payload["items"]),open_payload["total"])
        request=urllib.request.Request(self.server.url+"/api/stimpy/shitzo/status",data=b"{}",method="POST")
        with self.assertRaises(urllib.error.HTTPError) as caught: urllib.request.urlopen(request,timeout=2)
        self.assertEqual(405,caught.exception.code)


if __name__=="__main__": unittest.main()

import tempfile,unittest,urllib.error,urllib.request
from pathlib import Path

from stimpy.api import ReadOnlyAPI,StimpyApiServer
from stimpy.knowledge_graph import build_graph
from stimpy.learning_service import LearningService
from stimpy.memory_service import MemoryService
from stimpy.observation_store import ObservationStore


class HypothesisControlcenterTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name); self.store=ObservationStore(self.root/"database"/"stimpy.sqlite3",self.root); memory=MemoryService(self.store); self.server=StimpyApiServer(ReadOnlyAPI(self.store,memory,LearningService(memory),build_graph),port=0); self.server.start()
    def tearDown(self):
        self.server.stop(); self.store.close(); self.temp.cleanup()
    def get(self,path): return urllib.request.urlopen(self.server.url+path,timeout=2)
    def test_controlcenter_assets_are_local_responsive_and_hardened(self):
        response=self.get("/controlcenter"); html=response.read().decode(); self.assertIn("Stimpy Live-Controlcenter",html); self.assertIn('name="viewport"',html); self.assertEqual(response.headers["X-Content-Type-Options"],"nosniff"); self.assertIn("frame-ancestors 'none'",response.headers["Content-Security-Policy"])
        css=self.get("/controlcenter/app.css").read().decode(); self.assertIn("@media(max-width:820px)",css); self.assertIn("auto-fit",css)
        script=self.get("/controlcenter/app.js").read().decode(); self.assertIn("/api/stimpy/hypotheses",script); self.assertIn("/api/stimpy/training-runs",script); self.assertIn("/api/stimpy/shitzo/status",script); self.assertIn("Letzte Entscheidungen",script); self.assertIn("Offene Positionen",script); self.assertIn("/lifecycle",script); self.assertNotIn('method:\"POST\"',script); self.assertNotIn("innerHTML",script); self.assertNotIn(".style.",script)
    def test_controlcenter_is_get_only_and_does_not_mutate_storage(self):
        before={name:self.store.count(name) for name in ("hypotheses","hypothesis_evidence","hypothesis_lifecycle_events")}; request=urllib.request.Request(self.server.url+"/controlcenter",data=b"{}",method="POST")
        with self.assertRaises(urllib.error.HTTPError) as caught: urllib.request.urlopen(request,timeout=2)
        self.assertEqual(caught.exception.code,405); self.assertEqual(before,{name:self.store.count(name) for name in before})
    def test_assets_reject_unknown_paths(self):
        with self.assertRaises(urllib.error.HTTPError) as caught: self.get("/controlcenter/unknown.js")
        self.assertEqual(caught.exception.code,404)


if __name__=="__main__": unittest.main()

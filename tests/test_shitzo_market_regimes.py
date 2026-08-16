import json,tempfile,unittest,urllib.error,urllib.request
from datetime import UTC,datetime,timedelta
from pathlib import Path

from stimpy.api import ReadOnlyAPI,StimpyApiServer
from stimpy.knowledge_graph import build_graph
from stimpy.learning_service import LearningService
from stimpy.memory_service import MemoryService
from stimpy.observation_store import ObservationStore
from stimpy.shitzo.models import Direction,FeatureSnapshot,TraderDecision
from stimpy.shitzo.paper_broker import PaperBroker,PaperBrokerRules
from stimpy.shitzo.regime_analysis import RegimeAnalysisService
from stimpy.shitzo.regime_classifier import MarketRegimeClassifier,RegimeRules
from stimpy.shitzo.repository import ShitzoRepository

NOW=datetime(2026,1,1,tzinfo=UTC)
class ShitzoMarketRegimeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.db=self.root/"database"/"stimpy.sqlite3";self.store=ObservationStore(self.db,self.root);self.repo=ShitzoRepository(self.db);self.classifier=MarketRegimeClassifier();self.analysis=RegimeAnalysisService(self.repo,self.classifier,1)
        self.repo.create_run("run-regime",{"mode":"paper","regime_classifier":{"version":"shitzo-regime-v1"}});self.repo.start_run("run-regime",NOW);self.repo.create_account("run-regime","shitzo-trend",10000,NOW)
    def tearDown(self):
        if hasattr(self,"server"):self.server.stop()
        self.repo.close();self.store.close();self.temp.cleanup()
    def snapshot(self,key,spread=.001,momentum=.002,volatility=.0002):
        long_ma=100;short_ma=long_ma*(1+spread);return FeatureSnapshot(key,"BTC-USD",NOW,NOW-timedelta(minutes=19),NOW,short_ma,short_ma,long_ma,momentum,volatility,20,"fixture",tuple(f"{key}-{i}" for i in range(20)))
    def test_classifier_is_deterministic_transparent_and_lookahead_free(self):
        cases=((.001,.002,.00005,"UP_TREND_LOW_VOLATILITY"),(-.001,-.002,.0002,"DOWN_TREND_NORMAL_VOLATILITY"),(.00001,.003,.0007,"RANGE_HIGH_VOLATILITY"))
        for index,(spread,momentum,volatility,expected) in enumerate(cases):
            snapshot=self.snapshot(str(index),spread,momentum,volatility);first=self.classifier.classify(snapshot,"run-regime",classified_at=NOW);second=self.classifier.classify(snapshot,"run-regime",classified_at=NOW+timedelta(days=1));self.assertEqual(expected,first.combined_regime);self.assertEqual(first.label_id,second.label_id);self.assertIn("ma_spread",first.reasons[0])
    def test_live_label_persists_idempotently_and_backfill_does_not_rewrite_snapshot(self):
        snapshot=self.snapshot("live");self.repo.save_snapshot("run-regime",snapshot);label=self.classifier.classify(snapshot,"run-regime",classified_at=NOW);self.assertEqual(1,self.repo.save_regime_label(label));self.assertEqual(0,self.repo.save_regime_label(label));self.assertEqual("LIVE",self.repo.list_regimes()[0]["source_type"])
        old=self.snapshot("old",-.001,-.002,.0006);self.repo.save_snapshot("run-regime",old);self.assertEqual(1,self.analysis.backfill());self.assertEqual(0,self.analysis.backfill());labels={x["snapshot_id"]:x for x in self.repo.list_regimes()};self.assertEqual("HISTORICAL_BACKFILL",labels["old"]["source_type"]);self.assertEqual("DOWN_TREND_HIGH_VOLATILITY",labels["old"]["combined_regime"])
    def _trade(self,key,win):
        snapshot=self.snapshot(key);self.repo.save_snapshot("run-regime",snapshot);self.repo.save_regime_label(self.classifier.classify(snapshot,"run-regime",classified_at=NOW));decision=TraderDecision("d-"+key,"shitzo-trend","BTC-USD",Direction.LONG,.7,"entry reason "+key,NOW,snapshot.snapshot_id,"trend-v1-threshold-0.000200");broker=PaperBroker(self.repo,PaperBrokerRules());position=broker.consider("run-regime",decision,snapshot);price=position.take_profit if win else position.stop_loss;return broker.update_price(position,price,NOW+timedelta(minutes=5 if win else 7))
    def test_performance_and_loss_reason_are_joined_by_entry_regime(self):
        self._trade("win",True);self._trade("loss",False);item=self.analysis.performance("run-regime")[0];self.assertEqual(2,item["trades"]);self.assertEqual(.5,item["win_rate"]);self.assertEqual(.5,item["error_rate"]);self.assertGreater(item["profit_factor"],0);self.assertEqual("SUFFICIENT",item["case_status"]);loss=self.analysis.losses(run_id="run-regime")[0];self.assertEqual("STOP_LOSS",loss["exit_reason"]);self.assertEqual("entry reason loss",loss["decision_reason"]);self.assertEqual("UP_TREND_NORMAL_VOLATILITY",loss["combined_regime"])
    def test_get_only_regime_api(self):
        self._trade("api",False);memory=MemoryService(self.store);api=ReadOnlyAPI(self.store,memory,LearningService(memory),build_graph,shitzo_repository=self.repo,shitzo_regime_analysis=self.analysis);self.server=StimpyApiServer(api,port=0);self.server.start()
        for endpoint in ("regimes","regimes/current","regime-distribution","regime-performance","regime-losses"):
            response=urllib.request.urlopen(f"{self.server.url}/api/stimpy/shitzo/{endpoint}?run_id=run-regime",timeout=2);self.assertEqual(200,response.status);self.assertIsInstance(json.load(response)["items"],list)
        request=urllib.request.Request(self.server.url+"/api/stimpy/shitzo/regimes",data=b"{}",method="POST")
        with self.assertRaises(urllib.error.HTTPError) as caught:urllib.request.urlopen(request,timeout=2)
        self.assertEqual(405,caught.exception.code)

if __name__=="__main__":unittest.main()

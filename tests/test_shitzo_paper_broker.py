import tempfile, unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from stimpy.observation_store import ObservationStore
from stimpy.shitzo.models import Direction, FeatureSnapshot, TraderDecision
from stimpy.shitzo.paper_broker import PaperBroker, PaperBrokerRules
from stimpy.shitzo.repository import ShitzoRepository


class PaperBrokerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name); self.db=self.root/"database"/"stimpy.sqlite3"
        store=ObservationStore(self.db,self.root); store.close(); self.repo=ShitzoRepository(self.db); self.repo.create_run("run-1",{"mode":"paper"}); self.now=datetime(2026,1,1,tzinfo=UTC); self.repo.create_account("run-1","trend",10_000,self.now); self.broker=PaperBroker(self.repo,PaperBrokerRules())
    def tearDown(self): self.repo.close(); self.tmp.cleanup()
    def snapshot(self,key="s1",price=100,symbol="BTC-USD"):
        return FeatureSnapshot(key,symbol,self.now,self.now-timedelta(minutes=19),self.now,price,99,98,.02,.01,20,"fixture",tuple(f"{key}-e{i}" for i in range(20)))
    def decision(self,snapshot,direction=Direction.LONG,confidence=.7,key="d1"):
        return TraderDecision(key,"trend",snapshot.symbol,direction,confidence,"fixture",self.now,snapshot.snapshot_id,"v1")
    def test_long_take_profit_updates_virtual_account_atomically(self):
        s=self.snapshot(); p=self.broker.consider("run-1",self.decision(s),s); self.assertIsNotNone(p); self.assertLessEqual(p.quantity*p.entry_price,10_000)
        trade=self.broker.update_price(p,p.take_profit,self.now+timedelta(minutes=1)); self.assertEqual("WIN",trade["result_type"])
        account=self.repo.get_account("run-1","trend"); self.assertEqual(1,account.trades); self.assertEqual(1,account.wins); self.assertGreater(account.balance,10_000)
        self.assertEqual(trade,self.broker.update_price(p,p.take_profit,self.now+timedelta(minutes=2)))
        self.assertEqual(1,self.repo.get_account("run-1","trend").trades)
    def test_short_stop_loss_and_drawdown(self):
        s=self.snapshot(); p=self.broker.consider("run-1",self.decision(s,Direction.SHORT),s); trade=self.broker.update_price(p,p.stop_loss,self.now+timedelta(minutes=1)); self.assertEqual("LOSS",trade["result_type"])
        account=self.repo.get_account("run-1","trend"); self.assertEqual(1,account.losses); self.assertGreater(account.max_drawdown,0); self.assertLess(account.balance,10_000)
    def test_wait_low_confidence_and_second_open_position_fail_closed(self):
        s=self.snapshot(); self.assertIsNone(self.broker.consider("run-1",self.decision(s,Direction.WAIT,key="wait"),s))
        s2=self.snapshot("s2"); self.assertIsNone(self.broker.consider("run-1",self.decision(s2,confidence=.4,key="low"),s2))
        s3=self.snapshot("s3"); self.assertIsNotNone(self.broker.consider("run-1",self.decision(s3,key="open"),s3))
        s4=self.snapshot("s4"); self.assertIsNone(self.broker.consider("run-1",self.decision(s4,key="duplicate-open"),s4))
        eth=self.snapshot("eth",200,"ETH-USD"); self.assertIsNone(self.broker.consider("run-1",self.decision(eth,key="aggregate-no-leverage"),eth))
    def test_restart_preserves_open_position_and_account(self):
        s=self.snapshot(); position=self.broker.consider("run-1",self.decision(s),s); self.repo.close(); self.repo=ShitzoRepository(self.db); self.broker=PaperBroker(self.repo)
        restored=self.repo.get_open_position("run-1","trend","BTC-USD"); self.assertEqual(position,restored); self.assertEqual(10_000,self.repo.get_account("run-1","trend").balance)
    def test_repository_has_foreign_keys_and_broker_has_no_network_client(self):
        self.assertEqual(1,self.repo._db.execute("PRAGMA foreign_keys").fetchone()[0]); self.assertEqual([],self.repo._db.execute("PRAGMA foreign_key_check").fetchall())
        self.assertFalse(hasattr(self.broker,"client")); self.assertFalse(hasattr(self.broker,"exchange"))


if __name__=="__main__": unittest.main()

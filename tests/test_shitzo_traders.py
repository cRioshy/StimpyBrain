import unittest
from datetime import UTC,datetime,timedelta
from stimpy.shitzo.models import Direction,FeatureSnapshot
from stimpy.shitzo.traders import ContrarianTrader,MomentumTrader,TrendTrader
from stimpy.shitzo.traders.base import InsufficientDataError


class ShitzoTraderTests(unittest.TestCase):
    def snapshot(self,key="s",price=100,short_ma=100,long_ma=100,momentum=0):
        now=datetime(2026,1,1,tzinfo=UTC)
        return FeatureSnapshot(key,"BTC-USD",now,now-timedelta(minutes=19),now,price,short_ma,long_ma,momentum,.01,20,"fixture",tuple(f"{key}-{i}" for i in range(20)))
    def assert_decision(self,trader,snapshot,direction):
        first=trader.decide(snapshot); second=trader.decide(snapshot)
        self.assertEqual(direction,first.direction); self.assertEqual(first,second); self.assertEqual(snapshot.snapshot_id,first.feature_snapshot_id)
        self.assertLessEqual(first.confidence,.75); self.assertTrue(first.reason)
        if direction is Direction.WAIT: self.assertEqual(0,first.confidence)
        else: self.assertGreaterEqual(first.confidence,.55)
    def test_trend_long_short_wait_and_insufficient(self):
        trader=TrendTrader(threshold=.001)
        self.assert_decision(trader,self.snapshot("tl",short_ma=101,long_ma=100),Direction.LONG)
        self.assert_decision(trader,self.snapshot("ts",short_ma=99,long_ma=100),Direction.SHORT)
        self.assert_decision(trader,self.snapshot("tw",short_ma=100.05,long_ma=100),Direction.WAIT)
        with self.assertRaises(InsufficientDataError): trader.decide(None)
    def test_momentum_long_short_wait(self):
        trader=MomentumTrader(threshold=.003)
        self.assert_decision(trader,self.snapshot("ml",momentum=.01),Direction.LONG)
        self.assert_decision(trader,self.snapshot("ms",momentum=-.01),Direction.SHORT)
        self.assert_decision(trader,self.snapshot("mw",momentum=.001),Direction.WAIT)
    def test_contrarian_long_short_wait(self):
        trader=ContrarianTrader(threshold=.005)
        self.assert_decision(trader,self.snapshot("cl",price=98,long_ma=100),Direction.LONG)
        self.assert_decision(trader,self.snapshot("cs",price=102,long_ma=100),Direction.SHORT)
        self.assert_decision(trader,self.snapshot("cw",price=100.2,long_ma=100),Direction.WAIT)
    def test_rules_are_configurable_and_confidence_is_capped(self):
        decision=MomentumTrader(threshold=.0001,max_confidence=.60).decide(self.snapshot("cap",momentum=.5))
        self.assertEqual(.60,decision.confidence)
        with self.assertRaises(ValueError): TrendTrader(threshold=0)
    def test_default_thresholds_are_the_approved_half_values(self):
        self.assertEqual(.0005,TrendTrader().rules.threshold)
        self.assertEqual(.0015,MomentumTrader().rules.threshold)
        self.assertEqual(.0025,ContrarianTrader().rules.threshold)


if __name__=="__main__": unittest.main()

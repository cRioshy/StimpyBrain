import ast
import math
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from stimpy.config import StimpyConfig
from stimpy.observation_store import ObservationStore
from stimpy.shitzo.market_feed import validate_read_only_feed
from stimpy.shitzo.models import Direction, MarketTick, TraderDecision
from stimpy.shitzo.price_window import PriceWindow


class ReadFeed:
    source_name = "test-public-feed"
    def read_latest(self, symbol):
        return MarketTick(symbol, 100, datetime.now(UTC), self.source_name, "event")


class WriteCapableFeed(ReadFeed):
    def place_order(self): pass


class ShitzoFoundationTests(unittest.TestCase):
    def tick(self, number, price=None):
        return MarketTick("BTC-USD", price or 100 + number, datetime(2026, 1, 1, tzinfo=UTC) + timedelta(minutes=number), "test-public-feed", f"event-{number}")

    def test_models_reject_invalid_numbers_symbols_and_confidence(self):
        for value in (0, -1, math.nan, math.inf):
            with self.assertRaises(ValueError): MarketTick("BTC-USD", value, datetime.now(UTC), "source", "event")
        for symbol in ("BTC-USD","ETH-USD","XRP-USD","SOL-USD","ADA-USD","DOGE-USD"):
            self.assertEqual(symbol,MarketTick(symbol,1,datetime.now(UTC),"source",f"event-{symbol}").symbol)
        with self.assertRaises(ValueError): MarketTick("SHIB-USD", 1, datetime.now(UTC), "source", "event")
        with self.assertRaises(ValueError):
            TraderDecision("d", "t", "BTC-USD", Direction.WAIT, 1.1, "reason", datetime.now(UTC), "s", "v1")

    def test_price_window_is_chronological_bounded_and_frozen(self):
        window = PriceWindow("BTC-USD", short_period=2, long_period=4)
        for i in range(4): self.assertTrue(window.add(self.tick(i)))
        first = window.snapshot()
        self.assertEqual(4, first.sample_count)
        self.assertEqual(("event-0", "event-1", "event-2", "event-3"), first.source_data_ids)
        window.add(self.tick(4, 150))
        second = window.snapshot()
        self.assertNotEqual(first.snapshot_id, second.snapshot_id)
        self.assertEqual(103.0, first.price)
        self.assertEqual(150.0, second.price)
        with self.assertRaises(ValueError): window.add(self.tick(3))

    def test_feed_contract_rejects_write_capabilities(self):
        validate_read_only_feed(ReadFeed())
        with self.assertRaises(TypeError): validate_read_only_feed(WriteCapableFeed())

    def test_disabled_config_and_schema_v12_are_restart_safe(self):
        config=StimpyConfig.from_env();self.assertFalse(config.shitzo_enabled);self.assertEqual(("BTC-USD","ETH-USD","XRP-USD","SOL-USD","ADA-USD","DOGE-USD"),config.shitzo_symbols);config.validate()
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "database" / "stimpy.sqlite3"
            store = ObservationStore(db, Path(tmp))
            self.assertEqual(16, store.schema_version)
            tables = {row[0] for row in store._db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'shitzo_%'")}
            self.assertEqual(11, len(tables))
            self.assertEqual([], store._db.execute("PRAGMA foreign_key_check").fetchall())
            store.close()
            reopened = ObservationStore(db, Path(tmp))
            self.assertEqual(16, reopened.schema_version)
            reopened.close()

    def test_package_has_no_network_or_order_execution_calls(self):
        root = Path(__file__).parents[1] / "stimpy" / "shitzo"
        forbidden_calls = {"create_order", "place_order", "cancel_order", "transfer", "withdraw"}
        forbidden_imports = {"ccxt", "binance", "coinbase", "krakenex", "requests", "httpx", "urllib"}
        for path in root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    names = [alias.name.split(".")[0] for alias in node.names] if isinstance(node, ast.Import) else [(node.module or "").split(".")[0]]
                    self.assertTrue(forbidden_imports.isdisjoint(names), path.name)
                if isinstance(node, ast.Call):
                    name = node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id if isinstance(node.func, ast.Name) else ""
                    self.assertNotIn(name, forbidden_calls, path.name)


if __name__ == "__main__": unittest.main()

import tempfile
import time
import unittest
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

from stimpy.config import StimpyConfig
from stimpy.observation_store import ObservationStore
from stimpy.shitzo.lab import ShitzoLab
from stimpy.shitzo.models import MarketTick
from stimpy.shitzo.repository import ShitzoRepository
from stimpy.shitzo_collector import ShitzoCollector


class FixtureFeed:
    source_name = "fixture-read-only"

    def __init__(self):
        self.count = 0

    def read_latest(self, symbol):
        self.count += 1
        return MarketTick(symbol, 100 + self.count / 1000,
                          datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=self.count),
                          self.source_name, f"fixture-{self.count}")


class ShitzoCollectorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db = self.root / "database" / "stimpy.sqlite3"
        self.store = ObservationStore(self.db, self.root)
        base = StimpyConfig.from_env()
        self.config = replace(base, data_dir=self.root, database_file=self.db,
                              shitzo_enabled=True, shitzo_autorun=True,
                              shitzo_poll_interval_seconds=1, shutdown_timeout_seconds=3)
        self.repo = ShitzoRepository(self.db)
        self.lab = ShitzoLab(self.repo, self.config)

    def tearDown(self):
        self.repo.close()
        self.store.close()
        self.tmp.cleanup()

    def test_continuous_collector_starts_persists_and_stops_cleanly(self):
        collector = ShitzoCollector(self.config, self.lab, FixtureFeed())
        self.assertTrue(collector.start())
        deadline = time.monotonic() + 2
        while collector.ticks < 3 and time.monotonic() < deadline:
            time.sleep(.02)
        self.assertGreaterEqual(collector.ticks, 3)
        self.assertEqual("RUNNING", collector.status)
        self.assertEqual("RUNNING", self.repo.get_run(collector.run_id)["status"])
        collector.stop()
        self.assertEqual("STOPPED", collector.status)
        self.assertEqual("STOPPED", self.repo.get_run(collector.run_id)["status"])
        self.assertFalse(collector.snapshot()["real_orders"])

    def test_autorun_disabled_does_not_create_a_run(self):
        collector = ShitzoCollector(replace(self.config, shitzo_autorun=False), self.lab, FixtureFeed())
        self.assertFalse(collector.start())
        self.assertEqual("DISABLED", collector.status)
        self.assertEqual(0, self.repo.count("shitzo_lab_runs"))


if __name__ == "__main__":
    unittest.main()

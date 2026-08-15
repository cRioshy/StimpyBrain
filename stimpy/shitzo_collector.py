"""Explicitly enabled continuous paper-data collector with bounded shutdown."""
from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from threading import Event, Lock, Thread

from .shitzo.market_feed import validate_read_only_feed


class ShitzoCollector:
    _instance_lock = Lock()
    _active = False

    def __init__(self, config, lab, feed):
        validate_read_only_feed(feed)
        self.config, self.lab, self.feed = config, lab, feed
        self._stop = Event()
        self._thread = None
        self.status = "STOPPED"
        self.run_id = None
        self.ticks = 0
        self.failures = 0
        self.last_tick_at = None
        self.last_error = None
        self.state_file = config.data_dir / "state" / "shitzo_collector.json"

    @property
    def active(self):
        return bool(self._thread and self._thread.is_alive())

    def start(self):
        if not self.config.shitzo_autorun:
            self.status = "DISABLED"
            self._write_state()
            return False
        if not self.config.shitzo_enabled:
            raise RuntimeError("SHITZO_ENABLED must be true for autorun")
        with self._instance_lock:
            if ShitzoCollector._active:
                raise RuntimeError("Shitzo collector already active")
            ShitzoCollector._active = True
        self._stop.clear()
        self.status = "STARTING"
        self._write_state()
        self._thread = Thread(target=self._run, name="shitzo-paper-collector", daemon=False)
        self._thread.start()
        return True

    def _run(self):
        try:
            now = datetime.now(UTC)
            self.run_id = self.lab.start(f"continuous-paper-{now.strftime('%Y%m%d-%H%M%S')}", now)
            self.status = "RUNNING"
            self._write_state()
            while not self._stop.is_set():
                for symbol in self.config.shitzo_symbols:
                    if self._stop.is_set():
                        break
                    try:
                        tick = self.feed.read_latest(symbol)
                        self.lab.process_tick(tick, datetime.now(UTC))
                        self.ticks += 1
                        self.last_tick_at = tick.timestamp.isoformat()
                        self.last_error = None
                    except Exception as error:
                        self.failures += 1
                        self.last_error = str(error)
                self._write_state()
                self._stop.wait(self.config.shitzo_poll_interval_seconds)
        except Exception as error:
            self.status = "ERROR"
            self.last_error = str(error)
            self._write_state()
        finally:
            if self.lab.active:
                self.lab.stop(datetime.now(UTC))
            if self.status != "ERROR":
                self.status = "STOPPED"
            self._write_state()
            with self._instance_lock:
                ShitzoCollector._active = False

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(self.config.shutdown_timeout_seconds)
        if self._thread and self._thread.is_alive():
            raise TimeoutError("Shitzo collector did not stop")

    def snapshot(self):
        return {"status": self.status, "active": self.active, "automatic": self.config.shitzo_autorun,
                "live_provider": self.config.shitzo_autorun, "real_orders": False,
                "provider": self.feed.source_name, "run_id": self.run_id, "ticks": self.ticks,
                "failures": self.failures, "last_tick_at": self.last_tick_at,
                "last_error": self.last_error, "updated_at": datetime.now(UTC).isoformat()}

    def _write_state(self):
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        temp = self.state_file.with_suffix(".tmp")
        temp.write_text(json.dumps(self.snapshot(), sort_keys=True), encoding="utf-8")
        os.replace(temp, self.state_file)

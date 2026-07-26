"""Thread-safe, append-only observation persistence."""
from __future__ import annotations
import json, sqlite3
from pathlib import Path
from threading import RLock
from .models import Observation
from .workflow.sanitizer import AuditSanitizer

class ObservationStore:
    def __init__(self, path: str | Path, sanitizer: AuditSanitizer | None = None):
        self.path = Path(path); self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock(); self._sanitizer = sanitizer or AuditSanitizer()
        self._db = sqlite3.connect(self.path, check_same_thread=False); self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA foreign_keys=ON")
        if self._db.execute("PRAGMA quick_check").fetchone()[0] != "ok": raise sqlite3.DatabaseError("broken SQLite database")
        with self._db:
            self._db.execute("""CREATE TABLE IF NOT EXISTS observations(id INTEGER PRIMARY KEY, event_id TEXT UNIQUE NOT NULL, correlation_id TEXT NOT NULL, topic TEXT NOT NULL, source TEXT NOT NULL, market TEXT NOT NULL, symbol TEXT NOT NULL, observed_at TEXT NOT NULL, payload TEXT NOT NULL)""")
            self._db.execute("CREATE INDEX IF NOT EXISTS idx_observation_topic_time ON observations(topic, observed_at)")
    def append(self, item: Observation) -> bool:
        with self._lock:
            try:
                with self._db: self._db.execute("INSERT INTO observations(event_id,correlation_id,topic,source,market,symbol,observed_at,payload) VALUES(?,?,?,?,?,?,?,?)", (item.event_id,item.correlation_id,item.topic,item.source,item.market,item.symbol,item.observed_at.isoformat(),self._sanitizer.dumps(item.payload)))
                return True
            except sqlite3.IntegrityError: return False
    def list(self, limit: int = 1000):
        with self._lock:
            rows=self._db.execute("SELECT * FROM observations ORDER BY id DESC LIMIT ?",(max(1,min(limit,10000)),)).fetchall()
            return [{**dict(r),"payload":json.loads(r["payload"])} for r in rows]
    @property
    def foreign_keys_enabled(self): return bool(self._db.execute("PRAGMA foreign_keys").fetchone()[0])
    def close(self): self._db.close()

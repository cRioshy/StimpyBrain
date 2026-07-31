"""Append-only rotating JSONL plus synchronized SQLite metadata/memory index."""
from __future__ import annotations
import json,os,sqlite3
from datetime import UTC,datetime
from pathlib import Path
from threading import RLock
from .models import KnowledgeEntry,KnowledgeStatus,MemoryRecord,Observation,parse_timestamp

SCHEMA="""
CREATE TABLE IF NOT EXISTS stimpy_schema_migrations(version INTEGER PRIMARY KEY,applied_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS observations(
 observation_id TEXT PRIMARY KEY,event_id TEXT NOT NULL,correlation_id TEXT NOT NULL,source TEXT NOT NULL,
 source_endpoint TEXT NOT NULL,source_type TEXT NOT NULL,observed_at TEXT NOT NULL,source_timestamp TEXT NOT NULL,
 symbol TEXT NOT NULL,market TEXT NOT NULL,content_hash TEXT NOT NULL,schema_version INTEGER NOT NULL,
 jsonl_file TEXT NOT NULL,byte_offset INTEGER NOT NULL,payload_size INTEGER NOT NULL,
 processing_status TEXT NOT NULL CHECK(processing_status IN ('STORED','EVALUATED','INVALID')),created_at TEXT NOT NULL);
CREATE UNIQUE INDEX IF NOT EXISTS ux_observation_event ON observations(event_id,source_endpoint);
CREATE UNIQUE INDEX IF NOT EXISTS ux_observation_content ON observations(content_hash,source_endpoint);
CREATE UNIQUE INDEX IF NOT EXISTS ux_observation_correlation_type ON observations(correlation_id,source_type);
CREATE INDEX IF NOT EXISTS ix_observation_time ON observations(observed_at DESC);
CREATE TABLE IF NOT EXISTS memories(
 memory_id TEXT PRIMARY KEY,memory_type TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,
 source_observation_ids TEXT NOT NULL,subject TEXT NOT NULL,relation TEXT NOT NULL,object TEXT NOT NULL,
 evidence_count INTEGER NOT NULL,contradiction_count INTEGER NOT NULL,confidence REAL NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('OBSERVED','REPEATED','PROVISIONAL','SUPPORTED','CONTRADICTED','ARCHIVED')),
 last_verified_at TEXT NOT NULL,content TEXT NOT NULL,schema_version INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS workflow_results(id TEXT PRIMARY KEY,observation_id TEXT NOT NULL UNIQUE,status TEXT NOT NULL,reasons TEXT NOT NULL,gates TEXT NOT NULL,created_at TEXT NOT NULL,FOREIGN KEY(observation_id) REFERENCES observations(observation_id));
CREATE TABLE IF NOT EXISTS knowledge_entries(
 knowledge_id TEXT PRIMARY KEY,observation_id TEXT NOT NULL UNIQUE,symbol TEXT NOT NULL,decision TEXT NOT NULL,
 evidence_score INTEGER NOT NULL,reasons TEXT NOT NULL,counterarguments TEXT NOT NULL,critic_issues TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('OBSERVED','PROVISIONAL','SUPPORTED','CONTRADICTED')),
 created_at TEXT NOT NULL,schema_version INTEGER NOT NULL,FOREIGN KEY(observation_id) REFERENCES observations(observation_id));
"""
class ObservationStore:
    def __init__(self,database_path,data_dir=None,rotation_bytes=134217728):
        self.path=Path(database_path); self.data_dir=Path(data_dir or self.path.parents[1]); self.observations_dir=self.data_dir/"observations"
        for part in (self.observations_dir,self.data_dir/"memory",self.data_dir/"state",self.data_dir/"database",self.data_dir/"logs"): part.mkdir(parents=True,exist_ok=True)
        self.rotation_bytes=rotation_bytes; self._lock=RLock(); self._db=sqlite3.connect(self.path,check_same_thread=False); self._db.row_factory=sqlite3.Row
        try:
            self._db.execute("PRAGMA foreign_keys=ON")
            if self._db.execute("PRAGMA quick_check").fetchone()[0]!="ok": raise sqlite3.DatabaseError("SQLite quick_check failed")
            self._migrate()
        except sqlite3.DatabaseError:
            self._db.close()
            raise
    def _migrate(self):
        with self._db:
            existing={r[1] for r in self._db.execute("PRAGMA table_info(observations)")}
            if existing and "observation_id" not in existing:
                self._db.execute("ALTER TABLE observations RENAME TO observations_v1_legacy")
            self._db.executescript(SCHEMA)
            columns={r[1] for r in self._db.execute("PRAGMA table_info(observations)")}
            for name,kind in (("decision","TEXT"),("confidence","REAL"),("outcome","TEXT"),("profit","REAL")):
                if name not in columns: self._db.execute(f"ALTER TABLE observations ADD COLUMN {name} {kind}")
            self._db.execute("INSERT OR IGNORE INTO stimpy_schema_migrations VALUES(?,?)",(3,datetime.now(UTC).isoformat()))
    @property
    def foreign_keys_enabled(self): return bool(self._db.execute("PRAGMA foreign_keys").fetchone()[0])
    @property
    def schema_version(self): return int(self._db.execute("SELECT MAX(version) FROM stimpy_schema_migrations").fetchone()[0])
    def duplicate_reason(self,o):
        checks=(("observation_id","observation_id",o.observation_id),("event_id","event_id",o.event_id),("content_hash","content_hash",o.content_hash))
        for reason,column,value in checks:
            if self._db.execute(f"SELECT 1 FROM observations WHERE {column}=? AND source_endpoint=?",(value,o.source_endpoint)).fetchone(): return reason
        if self._db.execute("SELECT 1 FROM observations WHERE correlation_id=? AND source_type=?",(o.correlation_id,o.source_type)).fetchone(): return "correlation_id"
        return None
    def _segment(self,line_size):
        files=sorted(self.observations_dir.glob("observations-*.jsonl")); path=files[-1] if files else self.observations_dir/"observations-000001.jsonl"
        if path.exists() and path.stat().st_size+line_size>self.rotation_bytes:
            number=int(path.stem.rsplit("-",1)[-1])+1; path=self.observations_dir/f"observations-{number:06d}.jsonl"
        return path
    def append(self,o):
        with self._lock:
            reason=self.duplicate_reason(o)
            if reason: return False,reason
            record={"observation_id":o.observation_id,"event_id":o.event_id,"correlation_id":o.correlation_id,"source":o.source,"source_endpoint":o.source_endpoint,"source_type":o.source_type,"observed_at":o.observed_at.isoformat(),"source_timestamp":o.source_timestamp.isoformat(),"symbol":o.symbol,"market":o.market,"payload":o.payload,"content_hash":o.content_hash,"schema_version":o.schema_version,"decision":o.decision,"confidence":o.confidence,"outcome":o.outcome,"profit":o.profit}
            line=(json.dumps(record,sort_keys=True,ensure_ascii=True,allow_nan=False,separators=(",",":"))+"\n").encode(); path=self._segment(len(line)); offset=path.stat().st_size if path.exists() else 0
            with path.open("ab") as handle: handle.write(line); handle.flush(); os.fsync(handle.fileno())
            try:
                with self._db: self._db.execute("""INSERT INTO observations(observation_id,event_id,correlation_id,source,source_endpoint,source_type,observed_at,source_timestamp,symbol,market,content_hash,schema_version,jsonl_file,byte_offset,payload_size,processing_status,created_at,decision,confidence,outcome,profit) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",(o.observation_id,o.event_id,o.correlation_id,o.source,o.source_endpoint,o.source_type,o.observed_at.isoformat(),o.source_timestamp.isoformat(),o.symbol,o.market,o.content_hash,o.schema_version,path.name,offset,len(line),"STORED",datetime.now(UTC).isoformat(),o.decision,o.confidence,o.outcome,o.profit))
            except sqlite3.IntegrityError: return False,"concurrent_duplicate"
            return True,None
    def _read_payload(self,row):
        path=self.observations_dir/row["jsonl_file"]
        try:
            with path.open("rb") as handle: handle.seek(row["byte_offset"]); raw=handle.readline()
            item=json.loads(raw); return item.get("payload",{})
        except (OSError,json.JSONDecodeError): return {"_storage_error":"unreadable_jsonl_record"}
    def list(self,limit=100,offset=0):
        limit=max(1,min(int(limit),1000)); offset=max(0,int(offset))
        with self._lock:
            rows=self._db.execute("SELECT * FROM observations ORDER BY created_at DESC LIMIT ? OFFSET ?",(limit,offset)).fetchall()
            return [{**dict(r),"payload":self._read_payload(r)} for r in rows]
    def exists(self,observation_id):
        with self._lock: return self._db.execute("SELECT 1 FROM observations WHERE observation_id=?",(observation_id,)).fetchone() is not None
    def load_recent(self,limit=100):
        return [Observation(
            row["observation_id"],row["event_id"],row["correlation_id"],row["source"],row["source_endpoint"],row["source_type"],
            parse_timestamp(row["observed_at"]),parse_timestamp(row["source_timestamp"]),row["symbol"],row["market"],row["payload"],
            row["content_hash"],int(row["schema_version"]),row.get("decision"),row.get("confidence"),row.get("outcome"),row.get("profit"))
            for row in self.list(limit)]
    def count(self,table="observations"):
        if table not in {"observations","memories","workflow_results","knowledge_entries"}: raise ValueError("invalid table")
        return int(self._db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
    def upsert_memory(self,m:MemoryRecord):
        with self._lock,self._db:
            self._db.execute("""INSERT INTO memories VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(memory_id) DO UPDATE SET updated_at=excluded.updated_at,source_observation_ids=excluded.source_observation_ids,evidence_count=excluded.evidence_count,contradiction_count=excluded.contradiction_count,confidence=excluded.confidence,status=excluded.status,last_verified_at=excluded.last_verified_at,content=excluded.content""",(m.memory_id,m.memory_type,m.created_at.isoformat(),m.updated_at.isoformat(),json.dumps(m.source_observation_ids),m.subject,m.relation,m.object,m.evidence_count,m.contradiction_count,m.confidence,m.status.value,m.last_verified_at.isoformat(),json.dumps(m.content,sort_keys=True),m.schema_version))
    def get_memory(self,memory_id):
        row=self._db.execute("SELECT * FROM memories WHERE memory_id=?",(memory_id,)).fetchone(); return dict(row) if row else None
    def memories_for(self,subject,relation):
        return [dict(r) for r in self._db.execute("SELECT * FROM memories WHERE subject=? AND relation=?",(subject,relation)).fetchall()]
    def list_memories(self,limit=100,offset=0):
        rows=self._db.execute("SELECT * FROM memories ORDER BY updated_at DESC LIMIT ? OFFSET ?",(max(1,min(limit,1000)),max(0,offset))).fetchall(); return [dict(r) for r in rows]
    def save_workflow_result(self,result_id,observation_id,status,reasons,gates):
        with self._lock,self._db: self._db.execute("INSERT OR IGNORE INTO workflow_results VALUES(?,?,?,?,?,?)",(result_id,observation_id,status,json.dumps(reasons),json.dumps(gates),datetime.now(UTC).isoformat()))
    def list_workflow_results(self,limit=100,offset=0): return [dict(r) for r in self._db.execute("SELECT * FROM workflow_results ORDER BY created_at DESC LIMIT ? OFFSET ?",(max(1,min(limit,1000)),max(0,offset))).fetchall()]
    def save_knowledge(self,entry:KnowledgeEntry):
        with self._lock,self._db:
            self._db.execute("INSERT OR IGNORE INTO knowledge_entries VALUES(?,?,?,?,?,?,?,?,?,?,?)",(entry.knowledge_id,entry.observation_id,entry.symbol,entry.decision,entry.evidence_score,json.dumps(entry.reasons),json.dumps(entry.counterarguments),json.dumps(entry.critic_issues),entry.status.value,entry.created_at.isoformat(),entry.schema_version))
        return self.get_knowledge(entry.knowledge_id)
    def get_knowledge(self,knowledge_id):
        row=self._db.execute("SELECT * FROM knowledge_entries WHERE knowledge_id=?",(knowledge_id,)).fetchone()
        return self._knowledge_from_row(row) if row else None
    def load_knowledge(self):
        rows=self._db.execute("SELECT * FROM knowledge_entries ORDER BY created_at ASC").fetchall()
        return [self._knowledge_from_row(row) for row in rows]
    @staticmethod
    def _knowledge_from_row(row):
        return KnowledgeEntry(row["knowledge_id"],row["observation_id"],row["symbol"],row["decision"],int(row["evidence_score"]),tuple(json.loads(row["reasons"])),tuple(json.loads(row["counterarguments"])),tuple(json.loads(row["critic_issues"])),KnowledgeStatus(row["status"]),parse_timestamp(row["created_at"]),int(row["schema_version"]))
    def validate_jsonl(self,path):
        valid=[]; corrupt=[]
        with Path(path).open("rb") as handle:
            for number,line in enumerate(handle,1):
                if not line.endswith(b"\n"): break
                try: valid.append(json.loads(line))
                except json.JSONDecodeError: corrupt.append(number)
        return valid,corrupt
    def close(self):
        with self._lock: self._db.close()

"""Append-only rotating JSONL plus synchronized SQLite metadata/memory index."""
from __future__ import annotations
import json,os,sqlite3
from datetime import UTC,datetime
from pathlib import Path
from threading import RLock
from .models import CriticResult,EvidenceResult,Hypothesis,HypothesisCreator,HypothesisEvaluation,HypothesisEvidence,HypothesisEvidenceDirection,HypothesisStatus,IncubationComparison,IncubationStatus,IncubationTask,KnowledgeEntry,KnowledgeStatus,MemoryRecord,Observation,Pattern,PatternStatus,ReasoningResult,parse_timestamp

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
FOUNDATION_RESULTS_SCHEMA="""
CREATE TABLE IF NOT EXISTS evidence_results(
 evidence_id TEXT PRIMARY KEY,observation_id TEXT NOT NULL UNIQUE,raw_score INTEGER NOT NULL,
 normalized_score REAL NOT NULL,quality_score REAL NOT NULL,supporting_evidence TEXT NOT NULL,
 contradicting_evidence TEXT NOT NULL,evidence_count INTEGER NOT NULL,created_at TEXT NOT NULL,
 schema_version INTEGER NOT NULL,FOREIGN KEY(observation_id) REFERENCES observations(observation_id));
CREATE TABLE IF NOT EXISTS reasoning_results(
 reasoning_id TEXT PRIMARY KEY,observation_id TEXT NOT NULL UNIQUE,evidence_id TEXT NOT NULL UNIQUE,
 evidence_score INTEGER NOT NULL,reasons TEXT NOT NULL,counterarguments TEXT NOT NULL,conclusion TEXT NOT NULL,confidence REAL NOT NULL,
 uncertainty REAL NOT NULL,assumptions TEXT NOT NULL,missing_information TEXT NOT NULL,created_at TEXT NOT NULL,
 schema_version INTEGER NOT NULL,FOREIGN KEY(observation_id) REFERENCES observations(observation_id),
 FOREIGN KEY(evidence_id) REFERENCES evidence_results(evidence_id));
CREATE TABLE IF NOT EXISTS critic_results(
 critic_id TEXT PRIMARY KEY,observation_id TEXT NOT NULL UNIQUE,reasoning_id TEXT NOT NULL UNIQUE,
 issues TEXT NOT NULL,severity TEXT NOT NULL CHECK(severity IN ('INFO','LOW','MEDIUM','HIGH','CRITICAL')),
 suggestions TEXT NOT NULL,calibration_warning INTEGER NOT NULL,created_at TEXT NOT NULL,
 schema_version INTEGER NOT NULL,FOREIGN KEY(observation_id) REFERENCES observations(observation_id),
 FOREIGN KEY(reasoning_id) REFERENCES reasoning_results(reasoning_id));
CREATE INDEX IF NOT EXISTS ix_evidence_created ON evidence_results(created_at DESC);
CREATE INDEX IF NOT EXISTS ix_reasoning_created ON reasoning_results(created_at DESC);
CREATE INDEX IF NOT EXISTS ix_critic_created ON critic_results(created_at DESC);
"""
INCUBATION_SCHEMA="""
CREATE TABLE IF NOT EXISTS incubation_tasks(
 incubation_id TEXT PRIMARY KEY,subject TEXT NOT NULL,question TEXT NOT NULL,
 initial_observation_id TEXT NOT NULL,initial_reasoning_id TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('NEW','INCUBATING','READY','RESOLVED','FAILED','CANCELLED')),
 created_at TEXT NOT NULL,reactivate_at TEXT NOT NULL,reactivated_at TEXT,final_reasoning_id TEXT,
 new_observation_ids TEXT NOT NULL,conclusion TEXT,comparison TEXT,failure_count INTEGER NOT NULL,
 last_error TEXT,schema_version INTEGER NOT NULL,
 FOREIGN KEY(initial_observation_id) REFERENCES observations(observation_id),
 FOREIGN KEY(initial_reasoning_id) REFERENCES reasoning_results(reasoning_id),
 FOREIGN KEY(final_reasoning_id) REFERENCES reasoning_results(reasoning_id));
CREATE INDEX IF NOT EXISTS ix_incubation_status_time ON incubation_tasks(status,reactivate_at);
"""
PATTERN_SCHEMA="""
CREATE TABLE IF NOT EXISTS patterns(
 pattern_id TEXT PRIMARY KEY,pattern_type TEXT NOT NULL,conditions TEXT NOT NULL,
 observed_cases INTEGER NOT NULL,positive_cases INTEGER NOT NULL,negative_cases INTEGER NOT NULL,
 unresolved_cases INTEGER NOT NULL,evidence_count INTEGER NOT NULL,contradiction_count INTEGER NOT NULL,
 confidence REAL NOT NULL,status TEXT NOT NULL CHECK(status IN ('OBSERVED','PROVISIONAL','SUPPORTED','CONTRADICTED','ARCHIVED')),
 created_at TEXT NOT NULL,updated_at TEXT NOT NULL,schema_version INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS pattern_cases(
 pattern_id TEXT NOT NULL,observation_id TEXT NOT NULL,evidence_id TEXT NOT NULL,independence_key TEXT NOT NULL,
 outcome TEXT NOT NULL,pattern_type TEXT NOT NULL,conditions TEXT NOT NULL,created_at TEXT NOT NULL,
 PRIMARY KEY(pattern_id,observation_id),UNIQUE(pattern_id,independence_key),
 FOREIGN KEY(pattern_id) REFERENCES patterns(pattern_id),FOREIGN KEY(observation_id) REFERENCES observations(observation_id),
 FOREIGN KEY(evidence_id) REFERENCES evidence_results(evidence_id));
CREATE INDEX IF NOT EXISTS ix_patterns_status_updated ON patterns(status,updated_at DESC);
CREATE INDEX IF NOT EXISTS ix_pattern_cases_pattern ON pattern_cases(pattern_id,created_at ASC);
"""
HYPOTHESIS_SCHEMA="""
CREATE TABLE IF NOT EXISTS hypotheses(
 hypothesis_id TEXT PRIMARY KEY,statement TEXT NOT NULL,question TEXT NOT NULL,created_by TEXT NOT NULL,
 required_data TEXT NOT NULL,status TEXT NOT NULL CHECK(status IN ('NEW','INVESTIGATING','INCUBATING','PROVISIONAL','SUPPORTED','CONTRADICTED','REJECTED','ARCHIVED')),
 confidence REAL NOT NULL,evidence_count INTEGER NOT NULL,contradiction_count INTEGER NOT NULL,neutral_count INTEGER NOT NULL,
 created_at TEXT NOT NULL,updated_at TEXT NOT NULL,last_evaluated_at TEXT,schema_version INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS hypothesis_evidence(
 evidence_id TEXT PRIMARY KEY,hypothesis_id TEXT NOT NULL,source TEXT NOT NULL,source_observation_ids TEXT NOT NULL,
 direction TEXT NOT NULL CHECK(direction IN ('SUPPORTING','CONTRADICTING','NEUTRAL')),strength REAL NOT NULL,quality REAL NOT NULL,
 description TEXT NOT NULL,observed_at TEXT NOT NULL,created_at TEXT NOT NULL,independence_key TEXT NOT NULL,schema_version INTEGER NOT NULL,
 UNIQUE(hypothesis_id,independence_key),FOREIGN KEY(hypothesis_id) REFERENCES hypotheses(hypothesis_id));
CREATE TABLE IF NOT EXISTS hypothesis_evaluations(
 evaluation_id TEXT PRIMARY KEY,hypothesis_id TEXT NOT NULL,status TEXT NOT NULL,evidence_ratio REAL NOT NULL,confidence REAL NOT NULL,
 supporting_count INTEGER NOT NULL,contradicting_count INTEGER NOT NULL,neutral_count INTEGER NOT NULL,
 weighted_support REAL NOT NULL,weighted_contradiction REAL NOT NULL,evidence_quality REAL NOT NULL,uncertainty REAL NOT NULL,
 source_count INTEGER NOT NULL,independent_case_count INTEGER NOT NULL,explanation TEXT NOT NULL,evaluated_at TEXT NOT NULL,schema_version INTEGER NOT NULL,
 FOREIGN KEY(hypothesis_id) REFERENCES hypotheses(hypothesis_id));
CREATE INDEX IF NOT EXISTS ix_hypotheses_status_created ON hypotheses(status,created_at DESC);
CREATE INDEX IF NOT EXISTS ix_hypothesis_evidence_hypothesis_time ON hypothesis_evidence(hypothesis_id,observed_at DESC);
CREATE INDEX IF NOT EXISTS ix_hypothesis_evaluations_hypothesis_time ON hypothesis_evaluations(hypothesis_id,evaluated_at DESC);
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
            knowledge_columns={r[1] for r in self._db.execute("PRAGMA table_info(knowledge_entries)")}
            for name in ("reasoning_id","critic_id"):
                if name not in knowledge_columns: self._db.execute(f"ALTER TABLE knowledge_entries ADD COLUMN {name} TEXT")
            self._db.executescript(FOUNDATION_RESULTS_SCHEMA)
            self._db.execute("INSERT OR IGNORE INTO stimpy_schema_migrations VALUES(?,?)",(4,datetime.now(UTC).isoformat()))
            self._db.executescript(INCUBATION_SCHEMA)
            self._db.execute("INSERT OR IGNORE INTO stimpy_schema_migrations VALUES(?,?)",(5,datetime.now(UTC).isoformat()))
            self._db.executescript(PATTERN_SCHEMA)
            self._db.execute("INSERT OR IGNORE INTO stimpy_schema_migrations VALUES(?,?)",(6,datetime.now(UTC).isoformat()))
            self._db.executescript(HYPOTHESIS_SCHEMA)
            self._db.execute("INSERT OR IGNORE INTO stimpy_schema_migrations VALUES(?,?)",(7,datetime.now(UTC).isoformat()))
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
    def get_observation(self,observation_id):
        with self._lock:
            row=self._db.execute("SELECT * FROM observations WHERE observation_id=?",(observation_id,)).fetchone()
            return {**dict(row),"payload":self._read_payload(row)} if row else None
    def load_recent(self,limit=100):
        return [Observation(
            row["observation_id"],row["event_id"],row["correlation_id"],row["source"],row["source_endpoint"],row["source_type"],
            parse_timestamp(row["observed_at"]),parse_timestamp(row["source_timestamp"]),row["symbol"],row["market"],row["payload"],
            row["content_hash"],int(row["schema_version"]),row.get("decision"),row.get("confidence"),row.get("outcome"),row.get("profit"))
            for row in self.list(limit)]
    def count(self,table="observations"):
        if table not in {"observations","memories","workflow_results","knowledge_entries","evidence_results","reasoning_results","critic_results","incubation_tasks","patterns","pattern_cases","hypotheses","hypothesis_evidence","hypothesis_evaluations"}: raise ValueError("invalid table")
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
            self._db.execute("""INSERT OR IGNORE INTO knowledge_entries
            (knowledge_id,observation_id,symbol,decision,evidence_score,reasons,counterarguments,
             critic_issues,status,created_at,schema_version,reasoning_id,critic_id)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",(entry.knowledge_id,entry.observation_id,entry.symbol,entry.decision,entry.evidence_score,json.dumps(entry.reasons),json.dumps(entry.counterarguments),json.dumps(entry.critic_issues),entry.status.value,entry.created_at.isoformat(),entry.schema_version,entry.reasoning_id,entry.critic_id))
        return self.get_knowledge(entry.knowledge_id)
    def get_knowledge(self,knowledge_id):
        row=self._db.execute("SELECT * FROM knowledge_entries WHERE knowledge_id=?",(knowledge_id,)).fetchone()
        return self._knowledge_from_row(row) if row else None
    def load_knowledge(self):
        rows=self._db.execute("SELECT * FROM knowledge_entries ORDER BY created_at ASC").fetchall()
        return [self._knowledge_from_row(row) for row in rows]
    @staticmethod
    def _knowledge_from_row(row):
        keys=set(row.keys())
        return KnowledgeEntry(row["knowledge_id"],row["observation_id"],row["symbol"],row["decision"],int(row["evidence_score"]),tuple(json.loads(row["reasons"])),tuple(json.loads(row["counterarguments"])),tuple(json.loads(row["critic_issues"])),KnowledgeStatus(row["status"]),parse_timestamp(row["created_at"]),int(row["schema_version"]),row["reasoning_id"] or "" if "reasoning_id" in keys else "",row["critic_id"] or "" if "critic_id" in keys else "")
    def save_evidence(self,result:EvidenceResult):
        with self._lock,self._db:
            self._db.execute("""INSERT OR IGNORE INTO evidence_results VALUES(?,?,?,?,?,?,?,?,?,?)""",(result.evidence_id,result.observation_id,result.score,result.normalized_score,result.quality_score,json.dumps(result.supporting_evidence),json.dumps(result.contradicting_evidence),result.evidence_count,result.created_at.isoformat(),result.schema_version))
        return self.get_evidence(result.evidence_id)
    def get_evidence(self,evidence_id):
        row=self._db.execute("SELECT * FROM evidence_results WHERE evidence_id=?",(evidence_id,)).fetchone()
        return self._evidence_from_row(row) if row else None
    def get_evidence_for_observation(self,observation_id):
        row=self._db.execute("SELECT * FROM evidence_results WHERE observation_id=?",(observation_id,)).fetchone()
        return self._evidence_from_row(row) if row else None
    def list_evidence(self,limit=100,offset=0):
        rows=self._db.execute("SELECT * FROM evidence_results ORDER BY created_at DESC LIMIT ? OFFSET ?",(max(1,min(int(limit),1000)),max(0,int(offset)))).fetchall()
        return [self._result_row(row) for row in rows]
    @staticmethod
    def _evidence_from_row(row):
        return EvidenceResult(int(row["raw_score"]),float(row["normalized_score"]),tuple(json.loads(row["supporting_evidence"])),tuple(json.loads(row["contradicting_evidence"])),int(row["evidence_count"]),parse_timestamp(row["created_at"]),row["evidence_id"],row["observation_id"],float(row["quality_score"]),int(row["schema_version"]))
    def save_reasoning(self,result:ReasoningResult):
        with self._lock,self._db:
            self._db.execute("""INSERT OR IGNORE INTO reasoning_results VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",(result.reasoning_id,result.observation_id,result.evidence_id,result.evidence_score,json.dumps(result.reasons),json.dumps(result.counterarguments),result.conclusion,result.confidence,result.uncertainty,json.dumps(result.assumptions),json.dumps(result.missing_information),result.created_at.isoformat(),result.schema_version))
        return self.get_reasoning(result.reasoning_id)
    def get_reasoning(self,reasoning_id):
        row=self._db.execute("SELECT * FROM reasoning_results WHERE reasoning_id=?",(reasoning_id,)).fetchone()
        return self._reasoning_from_row(row) if row else None
    def get_reasoning_for_observation(self,observation_id):
        row=self._db.execute("SELECT * FROM reasoning_results WHERE observation_id=?",(observation_id,)).fetchone()
        return self._reasoning_from_row(row) if row else None
    def list_reasoning(self,limit=100,offset=0):
        rows=self._db.execute("SELECT * FROM reasoning_results ORDER BY created_at DESC LIMIT ? OFFSET ?",(max(1,min(int(limit),1000)),max(0,int(offset)))).fetchall()
        return [self._result_row(row) for row in rows]
    @staticmethod
    def _reasoning_from_row(row):
        return ReasoningResult(row["observation_id"],int(row["evidence_score"]),tuple(json.loads(row["reasons"])),tuple(json.loads(row["counterarguments"])),row["conclusion"],float(row["confidence"]),float(row["uncertainty"]),parse_timestamp(row["created_at"]),row["reasoning_id"],row["evidence_id"],tuple(json.loads(row["assumptions"])),tuple(json.loads(row["missing_information"])),int(row["schema_version"]))
    def save_critic(self,result:CriticResult):
        with self._lock,self._db:
            self._db.execute("""INSERT OR IGNORE INTO critic_results VALUES(?,?,?,?,?,?,?,?,?)""",(result.critic_id,result.observation_id,result.reasoning_id,json.dumps(result.issues),result.severity,json.dumps(result.suggestions),int(result.calibration_warning),result.created_at.isoformat(),result.schema_version))
        return self.get_critic(result.critic_id)
    def get_critic(self,critic_id):
        row=self._db.execute("SELECT * FROM critic_results WHERE critic_id=?",(critic_id,)).fetchone()
        return self._critic_from_row(row) if row else None
    def list_critics(self,limit=100,offset=0):
        rows=self._db.execute("SELECT * FROM critic_results ORDER BY created_at DESC LIMIT ? OFFSET ?",(max(1,min(int(limit),1000)),max(0,int(offset)))).fetchall()
        return [self._result_row(row) for row in rows]
    def create_incubation(self,task:IncubationTask):
        with self._lock,self._db:
            self._db.execute("""INSERT OR IGNORE INTO incubation_tasks
            (incubation_id,subject,question,initial_observation_id,initial_reasoning_id,status,
             created_at,reactivate_at,reactivated_at,final_reasoning_id,new_observation_ids,
             conclusion,comparison,failure_count,last_error,schema_version)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",self._incubation_values(task))
        return self.get_incubation(task.incubation_id)
    def update_incubation(self,task:IncubationTask):
        with self._lock,self._db:
            cursor=self._db.execute("""UPDATE incubation_tasks SET status=?,reactivate_at=?,reactivated_at=?,
            final_reasoning_id=?,new_observation_ids=?,conclusion=?,comparison=?,failure_count=?,last_error=?
            WHERE incubation_id=?""",(task.status.value,task.reactivate_at.isoformat(),task.reactivated_at.isoformat() if task.reactivated_at else None,task.final_reasoning_id,json.dumps(task.new_observation_ids),task.conclusion,self._comparison_json(task.comparison),task.failure_count,task.last_error,task.incubation_id))
            if cursor.rowcount!=1: raise KeyError("unknown incubation task")
        return self.get_incubation(task.incubation_id)
    def get_incubation(self,incubation_id):
        row=self._db.execute("SELECT * FROM incubation_tasks WHERE incubation_id=?",(incubation_id,)).fetchone()
        return self._incubation_from_row(row) if row else None
    def list_incubations(self,limit=100,offset=0,status=None):
        limit=max(1,min(int(limit),1000)); offset=max(0,int(offset))
        if status is None: rows=self._db.execute("SELECT * FROM incubation_tasks ORDER BY created_at DESC LIMIT ? OFFSET ?",(limit,offset)).fetchall()
        else: rows=self._db.execute("SELECT * FROM incubation_tasks WHERE status=? ORDER BY reactivate_at ASC LIMIT ? OFFSET ?",(IncubationStatus(status).value,limit,offset)).fetchall()
        return [self._incubation_dict(row) for row in rows]
    def mark_due_incubations_ready(self,now):
        with self._lock,self._db:
            cursor=self._db.execute("UPDATE incubation_tasks SET status='READY' WHERE status='INCUBATING' AND reactivate_at<=?",(now.isoformat(),))
            return cursor.rowcount
    def add_pattern_case(self,pattern_id,pattern_type,conditions,observation,evidence_id,created_at):
        conditions_json=json.dumps(conditions,sort_keys=True,separators=(",",":"),ensure_ascii=True)
        now=parse_timestamp(created_at).isoformat()
        with self._lock,self._db:
            self._db.execute("""INSERT OR IGNORE INTO patterns
            (pattern_id,pattern_type,conditions,observed_cases,positive_cases,negative_cases,unresolved_cases,evidence_count,contradiction_count,confidence,status,created_at,updated_at,schema_version)
            VALUES(?,?,?,0,0,0,0,0,0,0,'OBSERVED',?,?,1)""",(pattern_id,pattern_type,conditions_json,now,now))
            cursor=self._db.execute("""INSERT OR IGNORE INTO pattern_cases
            (pattern_id,observation_id,evidence_id,independence_key,outcome,pattern_type,conditions,created_at)
            VALUES(?,?,?,?,?,?,?,?)""",(pattern_id,observation["observation_id"],evidence_id,observation["correlation_id"],observation.get("outcome") or "UNKNOWN",pattern_type,conditions_json,now))
            return cursor.rowcount==1
    def save_pattern(self,pattern:Pattern):
        with self._lock,self._db:
            cursor=self._db.execute("""UPDATE patterns SET observed_cases=?,positive_cases=?,negative_cases=?,unresolved_cases=?,
            evidence_count=?,contradiction_count=?,confidence=?,status=?,updated_at=? WHERE pattern_id=?""",
            (pattern.observed_cases,pattern.positive_cases,pattern.negative_cases,pattern.unresolved_cases,pattern.evidence_count,pattern.contradiction_count,pattern.confidence,pattern.status.value,pattern.updated_at.isoformat(),pattern.pattern_id))
            if cursor.rowcount!=1: raise KeyError("unknown pattern")
        return self.get_pattern(pattern.pattern_id)
    def get_pattern(self,pattern_id):
        row=self._db.execute("SELECT * FROM patterns WHERE pattern_id=?",(pattern_id,)).fetchone()
        return self._pattern_from_row(row) if row else None
    def list_patterns(self,limit=100,offset=0,status=None):
        limit=max(1,min(int(limit),1000)); offset=max(0,int(offset))
        if status is None: rows=self._db.execute("SELECT * FROM patterns ORDER BY updated_at DESC LIMIT ? OFFSET ?",(limit,offset)).fetchall()
        else: rows=self._db.execute("SELECT * FROM patterns WHERE status=? ORDER BY updated_at DESC LIMIT ? OFFSET ?",(PatternStatus(status).value,limit,offset)).fetchall()
        return [self._pattern_dict(row) for row in rows]
    def list_pattern_cases(self,pattern_id):
        return [dict(row) for row in self._db.execute("SELECT * FROM pattern_cases WHERE pattern_id=? ORDER BY created_at ASC",(pattern_id,)).fetchall()]
    def create_hypothesis(self,hypothesis:Hypothesis):
        with self._lock,self._db:
            self._db.execute("""INSERT OR IGNORE INTO hypotheses
            (hypothesis_id,statement,question,created_by,required_data,status,confidence,evidence_count,contradiction_count,neutral_count,created_at,updated_at,last_evaluated_at,schema_version)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",(hypothesis.hypothesis_id,hypothesis.statement,hypothesis.question,hypothesis.created_by.value,json.dumps(hypothesis.required_data),hypothesis.status.value,hypothesis.confidence,hypothesis.evidence_count,hypothesis.contradiction_count,hypothesis.neutral_count,hypothesis.created_at.isoformat(),hypothesis.updated_at.isoformat(),hypothesis.last_evaluated_at.isoformat() if hypothesis.last_evaluated_at else None,hypothesis.schema_version))
        return self.get_hypothesis(hypothesis.hypothesis_id)
    def get_hypothesis(self,hypothesis_id):
        row=self._db.execute("SELECT * FROM hypotheses WHERE hypothesis_id=?",(hypothesis_id,)).fetchone()
        return self._hypothesis_from_row(row) if row else None
    def get_hypothesis_dict(self,hypothesis_id):
        row=self._db.execute("SELECT * FROM hypotheses WHERE hypothesis_id=?",(hypothesis_id,)).fetchone()
        return self._hypothesis_dict(row) if row else None
    def list_hypotheses(self,limit=100,offset=0,status=None):
        limit=max(1,min(int(limit),1000)); offset=max(0,int(offset))
        if status is None: rows=self._db.execute("SELECT * FROM hypotheses ORDER BY created_at DESC LIMIT ? OFFSET ?",(limit,offset)).fetchall()
        else: rows=self._db.execute("SELECT * FROM hypotheses WHERE status=? ORDER BY created_at DESC LIMIT ? OFFSET ?",(HypothesisStatus(status).value,limit,offset)).fetchall()
        return [self._hypothesis_dict(row) for row in rows]
    def add_hypothesis_evidence(self,evidence:HypothesisEvidence):
        with self._lock,self._db:
            self._db.execute("""INSERT OR IGNORE INTO hypothesis_evidence
            (evidence_id,hypothesis_id,source,source_observation_ids,direction,strength,quality,description,observed_at,created_at,independence_key,schema_version)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",(evidence.evidence_id,evidence.hypothesis_id,evidence.source,json.dumps(evidence.source_observation_ids),evidence.direction.value,evidence.strength,evidence.quality,evidence.description,evidence.observed_at.isoformat(),evidence.created_at.isoformat(),evidence.independence_key,evidence.schema_version))
        stored=self.get_hypothesis_evidence(evidence.evidence_id)
        if stored is not None: return stored
        row=self._db.execute("SELECT * FROM hypothesis_evidence WHERE hypothesis_id=? AND independence_key=?",(evidence.hypothesis_id,evidence.independence_key)).fetchone()
        return self._hypothesis_evidence_from_row(row)
    def get_hypothesis_evidence(self,evidence_id):
        row=self._db.execute("SELECT * FROM hypothesis_evidence WHERE evidence_id=?",(evidence_id,)).fetchone()
        return self._hypothesis_evidence_from_row(row) if row else None
    def load_hypothesis_evidence(self,hypothesis_id):
        rows=self._db.execute("SELECT * FROM hypothesis_evidence WHERE hypothesis_id=? ORDER BY observed_at ASC,evidence_id ASC",(hypothesis_id,)).fetchall()
        return [self._hypothesis_evidence_from_row(row) for row in rows]
    def list_hypothesis_evidence(self,hypothesis_id,limit=100,offset=0):
        rows=self._db.execute("SELECT * FROM hypothesis_evidence WHERE hypothesis_id=? ORDER BY observed_at DESC LIMIT ? OFFSET ?",(hypothesis_id,max(1,min(int(limit),1000)),max(0,int(offset)))).fetchall()
        return [self._hypothesis_evidence_dict(row) for row in rows]
    def count_hypothesis_evidence(self,hypothesis_id):
        return int(self._db.execute("SELECT COUNT(*) FROM hypothesis_evidence WHERE hypothesis_id=?",(hypothesis_id,)).fetchone()[0])
    def save_hypothesis_evaluation(self,evaluation:HypothesisEvaluation):
        with self._lock,self._db:
            self._db.execute("""INSERT OR IGNORE INTO hypothesis_evaluations VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",(evaluation.evaluation_id,evaluation.hypothesis_id,evaluation.status.value,evaluation.evidence_ratio,evaluation.confidence,evaluation.supporting_count,evaluation.contradicting_count,evaluation.neutral_count,evaluation.weighted_support,evaluation.weighted_contradiction,evaluation.evidence_quality,evaluation.uncertainty,evaluation.source_count,evaluation.independent_case_count,evaluation.explanation,evaluation.evaluated_at.isoformat(),evaluation.schema_version))
        return self.get_hypothesis_evaluation(evaluation.evaluation_id)
    def get_hypothesis_evaluation(self,evaluation_id):
        row=self._db.execute("SELECT * FROM hypothesis_evaluations WHERE evaluation_id=?",(evaluation_id,)).fetchone()
        return self._hypothesis_evaluation_from_row(row) if row else None
    def latest_hypothesis_evaluation(self,hypothesis_id):
        row=self._db.execute("SELECT * FROM hypothesis_evaluations WHERE hypothesis_id=? ORDER BY evaluated_at DESC,rowid DESC LIMIT 1",(hypothesis_id,)).fetchone()
        return self._hypothesis_evaluation_dict(row) if row else None
    def update_hypothesis_evaluation(self,hypothesis_id,status,confidence,evidence_count,contradiction_count,neutral_count,evaluated_at):
        with self._lock,self._db:
            cursor=self._db.execute("""UPDATE hypotheses SET status=?,confidence=?,evidence_count=?,contradiction_count=?,neutral_count=?,updated_at=?,last_evaluated_at=? WHERE hypothesis_id=?""",(status.value,confidence,evidence_count,contradiction_count,neutral_count,evaluated_at.isoformat(),evaluated_at.isoformat(),hypothesis_id))
            if cursor.rowcount!=1: raise KeyError("unknown hypothesis")
        return self.get_hypothesis(hypothesis_id)
    @staticmethod
    def _pattern_from_row(row):
        return Pattern(row["pattern_id"],row["pattern_type"],json.loads(row["conditions"]),int(row["observed_cases"]),int(row["positive_cases"]),int(row["negative_cases"]),int(row["unresolved_cases"]),int(row["evidence_count"]),int(row["contradiction_count"]),float(row["confidence"]),PatternStatus(row["status"]),parse_timestamp(row["created_at"]),parse_timestamp(row["updated_at"]),int(row["schema_version"]))
    @classmethod
    def _pattern_dict(cls,row):
        pattern=cls._pattern_from_row(row)
        return {"pattern_id":pattern.pattern_id,"pattern_type":pattern.pattern_type,"conditions":pattern.conditions,"observed_cases":pattern.observed_cases,"positive_cases":pattern.positive_cases,"negative_cases":pattern.negative_cases,"unresolved_cases":pattern.unresolved_cases,"evidence_count":pattern.evidence_count,"contradiction_count":pattern.contradiction_count,"confidence":pattern.confidence,"status":pattern.status.value,"created_at":pattern.created_at.isoformat(),"updated_at":pattern.updated_at.isoformat(),"schema_version":pattern.schema_version}
    @staticmethod
    def _hypothesis_from_row(row):
        return Hypothesis(row["hypothesis_id"],row["statement"],row["question"],HypothesisCreator(row["created_by"]),parse_timestamp(row["created_at"]),parse_timestamp(row["updated_at"]),tuple(json.loads(row["required_data"])),HypothesisStatus(row["status"]),float(row["confidence"]),int(row["evidence_count"]),int(row["contradiction_count"]),int(row["neutral_count"]),parse_timestamp(row["last_evaluated_at"]) if row["last_evaluated_at"] else None,int(row["schema_version"]))
    @classmethod
    def _hypothesis_dict(cls,row):
        item=dict(row); item["required_data"]=list(json.loads(item["required_data"])); return item
    @staticmethod
    def _hypothesis_evidence_from_row(row):
        return HypothesisEvidence(row["evidence_id"],row["hypothesis_id"],row["source"],tuple(json.loads(row["source_observation_ids"])),HypothesisEvidenceDirection(row["direction"]),float(row["strength"]),float(row["quality"]),row["description"],parse_timestamp(row["observed_at"]),parse_timestamp(row["created_at"]),row["independence_key"],int(row["schema_version"]))
    @classmethod
    def _hypothesis_evidence_dict(cls,row):
        item=dict(row); item["source_observation_ids"]=list(json.loads(item["source_observation_ids"])); return item
    @staticmethod
    def _hypothesis_evaluation_from_row(row):
        return HypothesisEvaluation(row["evaluation_id"],row["hypothesis_id"],HypothesisStatus(row["status"]),float(row["evidence_ratio"]),float(row["confidence"]),int(row["supporting_count"]),int(row["contradicting_count"]),int(row["neutral_count"]),float(row["weighted_support"]),float(row["weighted_contradiction"]),float(row["evidence_quality"]),float(row["uncertainty"]),int(row["source_count"]),int(row["independent_case_count"]),row["explanation"],parse_timestamp(row["evaluated_at"]),int(row["schema_version"]))
    @classmethod
    def _hypothesis_evaluation_dict(cls,row):
        evaluation=cls._hypothesis_evaluation_from_row(row); item=dict(row); item["status"]=evaluation.status.value; return item
    @staticmethod
    def _comparison_json(comparison):
        if comparison is None: return None
        return json.dumps(comparison.__dict__,sort_keys=True)
    @classmethod
    def _incubation_values(cls,task):
        return (task.incubation_id,task.subject,task.question,task.initial_observation_id,task.initial_reasoning_id,task.status.value,task.created_at.isoformat(),task.reactivate_at.isoformat(),task.reactivated_at.isoformat() if task.reactivated_at else None,task.final_reasoning_id,json.dumps(task.new_observation_ids),task.conclusion,cls._comparison_json(task.comparison),task.failure_count,task.last_error,task.schema_version)
    @staticmethod
    def _incubation_from_row(row):
        comparison=IncubationComparison(**json.loads(row["comparison"])) if row["comparison"] else None
        return IncubationTask(row["incubation_id"],row["subject"],row["question"],row["initial_observation_id"],row["initial_reasoning_id"],IncubationStatus(row["status"]),parse_timestamp(row["created_at"]),parse_timestamp(row["reactivate_at"]),parse_timestamp(row["reactivated_at"]) if row["reactivated_at"] else None,row["final_reasoning_id"],tuple(json.loads(row["new_observation_ids"])),row["conclusion"],comparison,int(row["failure_count"]),row["last_error"],int(row["schema_version"]))
    @classmethod
    def _incubation_dict(cls,row):
        task=cls._incubation_from_row(row); result=dict(row); result["new_observation_ids"]=list(task.new_observation_ids); result["comparison"]=task.comparison.__dict__ if task.comparison else None; return result
    @staticmethod
    def _critic_from_row(row):
        return CriticResult(row["observation_id"],tuple(json.loads(row["issues"])),row["severity"],tuple(json.loads(row["suggestions"])),parse_timestamp(row["created_at"]),row["critic_id"],row["reasoning_id"],bool(row["calibration_warning"]),int(row["schema_version"]))
    @staticmethod
    def _result_row(row):
        item=dict(row)
        for key in ("supporting_evidence","contradicting_evidence","reasons","counterarguments","assumptions","missing_information","issues","suggestions"):
            if key in item: item[key]=json.loads(item[key])
        if "calibration_warning" in item: item["calibration_warning"]=bool(item["calibration_warning"])
        return item
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

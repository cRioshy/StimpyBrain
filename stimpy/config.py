"""Fail-safe Phase-2 configuration; Pandorick polling is disabled by default."""
from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT=Path(__file__).resolve().parents[1]
def _bool(name,default): return os.getenv(name,"1" if default else "0").strip().lower() in {"1","true","yes","on"}
def _int(name,default):
    try: return int(os.getenv(name,str(default)))
    except ValueError: return default
def _float(name,default):
    try: return float(os.getenv(name,str(default)))
    except ValueError: return default

@dataclass(frozen=True)
class StimpyConfig:
    enabled: bool=True
    mode: str="observe"
    read_only: bool=True
    pandorick_enabled: bool=False
    pandorick_base_url: str="http://127.0.0.1:8000"
    poll_interval_seconds: float=60.0
    request_timeout_seconds: float=5.0
    max_retries: int=2
    backoff_seconds: float=2.0
    observation_batch_limit: int=100
    max_payload_bytes: int=65_536
    data_dir: Path=PROJECT_ROOT/"stimpy_data"
    database_file: Path=PROJECT_ROOT/"stimpy_data"/"database"/"stimpy_memory.sqlite3"
    jsonl_rotation_bytes: int=134_217_728
    max_future_skew_seconds: float=5.0
    api_host: str="127.0.0.1"
    api_port: int=8765
    shutdown_timeout_seconds: float=10.0
    incubation_default_seconds: int=3600
    incubation_max_retries: int=3
    pattern_min_cases: int=25
    pattern_supported_min_cases: int=50
    confidence_max_provisional: float=.70
    pandorick_endpoints: tuple[str,...]=(
        "/api/v1/health","/api/v1/system/status","/api/v1/brain/status",
        "/api/v1/decisions/recent?limit=100","/api/v1/statistics","/api/v1/warnings")
    @classmethod
    def from_env(cls):
        data_dir=Path(os.getenv("STIMPY_DATA_DIR",str(cls.data_dir)))
        db=Path(os.getenv("STIMPY_DATABASE_FILE",str(data_dir/"database"/"stimpy_memory.sqlite3")))
        return cls(_bool("STIMPY_ENABLED",True),"observe",True,_bool("STIMPY_PANDORICK_ENABLED",False),
            os.getenv("STIMPY_PANDORICK_BASE_URL","http://127.0.0.1:8000"),max(1,_float("STIMPY_PANDORICK_POLL_INTERVAL_SECONDS",60)),
            max(.1,_float("STIMPY_PANDORICK_REQUEST_TIMEOUT_SECONDS",5)),max(0,min(_int("STIMPY_PANDORICK_MAX_RETRIES",2),5)),
            max(0,_float("STIMPY_PANDORICK_BACKOFF_SECONDS",2)),max(1,min(_int("STIMPY_OBSERVATION_BATCH_LIMIT",100),1000)),
            max(1024,_int("STIMPY_MAX_PAYLOAD_BYTES",65536)),data_dir,db,max(4096,_int("STIMPY_JSONL_ROTATION_BYTES",134217728)),
            max(0,_float("STIMPY_MAX_FUTURE_SKEW_SECONDS",5)),"127.0.0.1",max(1,min(_int("STIMPY_API_PORT",8765),65535)),10.0,
            max(1,_int("STIMPY_INCUBATION_DEFAULT_SECONDS",3600)),max(1,min(_int("STIMPY_INCUBATION_MAX_RETRIES",3),10)),
            max(2,_int("STIMPY_PATTERN_MIN_CASES",25)),max(2,_int("STIMPY_PATTERN_SUPPORTED_MIN_CASES",50)),max(0.0,min(_float("STIMPY_CONFIDENCE_MAX_PROVISIONAL",.70),.70)))
    def validate(self):
        if self.mode!="observe" or not self.read_only: raise ValueError("StimpyBrain is permanently observe/read-only")
        if not self.pandorick_base_url.startswith(("http://127.0.0.1","http://localhost")): raise ValueError("Pandorick URL must be local")

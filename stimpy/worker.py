"""Single-instance polling worker with atomic state and bounded shutdown."""
from __future__ import annotations
import json,os
from datetime import UTC,datetime
from pathlib import Path
from threading import Event,Lock,Thread

class StimpyWorker:
    _instance_lock=Lock(); _active=False
    def __init__(self,config,adapter,store,memory,workflow):
        self.config,self.adapter,self.store,self.memory,self.workflow=config,adapter,store,memory,workflow; self.status="STOPPED"; self._stop=Event(); self._thread=None; self._processed=set(); self._state_lock=Lock(); self.state_file=config.data_dir/"state"/"worker.json"
    def start(self):
        with self._instance_lock:
            if StimpyWorker._active: raise RuntimeError("Stimpy worker already active")
            StimpyWorker._active=True
        self.status="STARTING"; self._write_state(); self._thread=Thread(target=self._run,name="stimpy-worker",daemon=False); self._thread.start()
    def _run(self):
        self.status="RUNNING" if self.config.pandorick_enabled else "DISABLED"; self._write_state()
        while not self._stop.is_set():
            if self.config.pandorick_enabled:
                result=self.adapter.poll_once(); self.status=result["status"]; self._process_new()
            self._write_state(); self._stop.wait(self.config.poll_interval_seconds)
        self.status="STOPPED"; self._write_state()
    def _process_new(self):
        import asyncio
        for row in reversed(self.store.list(self.config.observation_batch_limit)):
            if row["observation_id"] in self._processed: continue
            self.memory.update_from_observation(row); result=asyncio.run(self.workflow.evaluate_observation(row)); self.store.save_workflow_result(result["id"],row["observation_id"],result["status"],result["reasons"],result["gates"]); self.adapter.events.emit("STIMPY_WORKFLOW_EVALUATED",observation_id=row["observation_id"],status=result["status"]); self._processed.add(row["observation_id"])
    def stop(self):
        self.status="STOPPING"; self._write_state(); self._stop.set()
        if self._thread: self._thread.join(self.config.shutdown_timeout_seconds)
        if self._thread and self._thread.is_alive(): self.status="ERROR"; self._write_state(); raise TimeoutError("Stimpy worker did not stop")
        with self._instance_lock: StimpyWorker._active=False
    def _write_state(self):
        with self._state_lock:
            self.state_file.parent.mkdir(parents=True,exist_ok=True); temp=self.state_file.with_suffix(".tmp"); temp.write_text(json.dumps(self.status_snapshot(),sort_keys=True),encoding="utf-8"); os.replace(temp,self.state_file)
    def status_snapshot(self):
        return {"version":"2.0.0","status":self.status,"mode":"observe","read_only":True,"pandorick_enabled":self.config.pandorick_enabled,"last_successful_observation":self.adapter.last_success,"last_error":self.adapter.last_error,**self.adapter.stats,"memory_entries":self.store.count("memories"),"workflow_evaluations":self.store.count("workflow_results"),"database_status":"OK","worker_alive":bool(self._thread and self._thread.is_alive()),"updated_at":datetime.now(UTC).isoformat()}

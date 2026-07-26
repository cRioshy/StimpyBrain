"""Failure-isolated Pandorick poll adapter; connection stays opt-in."""
from __future__ import annotations
from datetime import UTC,datetime
from .normalizer import ObservationNormalizer

class ObservationAdapter:
    def __init__(self,config,store,http_client,events,normalizer=None):
        config.validate(); self.config=config; self.store=store; self.client=http_client; self.events=events
        self.normalizer=normalizer or ObservationNormalizer(config.max_payload_bytes,config.max_future_skew_seconds)
        self.available=None; self.last_success=None; self.last_error=None; self.stats={"received":0,"stored":0,"duplicates":0,"invalid":0,"batches":0}
    def poll_once(self):
        if not self.config.pandorick_enabled: return {"status":"DISABLED","stored":0}
        stored=invalid=duplicates=0; successful=0
        for endpoint in self.config.pandorick_endpoints:
            try:
                envelope=self.client.get(endpoint); observations,errors=self.normalizer.normalize_envelope(endpoint,envelope,self.config.observation_batch_limit); invalid+=len(errors)
                for _ in errors: self.events.emit("STIMPY_OBSERVATION_INVALID",endpoint=endpoint)
                for observation in observations:
                    self.stats["received"]+=1; self.events.emit("STIMPY_OBSERVATION_RECEIVED",observation_id=observation.observation_id)
                    accepted,reason=self.store.append(observation)
                    if accepted: stored+=1; self.events.emit("STIMPY_OBSERVATION_STORED",observation_id=observation.observation_id)
                    else: duplicates+=1; self.events.emit("STIMPY_OBSERVATION_DUPLICATE",reason=reason)
                successful+=1
            except Exception as exc:
                invalid+=1; self.last_error=type(exc).__name__; self.events.emit("STIMPY_OBSERVATION_INVALID",endpoint=endpoint,error=type(exc).__name__)
        was=self.available; self.available=successful>0
        if self.available:
            self.last_success=datetime.now(UTC).isoformat()
            if was is False: self.events.emit("STIMPY_SOURCE_RECOVERED")
        else: self.events.emit("STIMPY_SOURCE_UNAVAILABLE"); self.last_error=self.last_error or "source unavailable"
        self.stats["stored"]+=stored; self.stats["duplicates"]+=duplicates; self.stats["invalid"]+=invalid; self.stats["batches"]+=1
        self.events.emit("STIMPY_BATCH_COMPLETED",stored=stored,duplicates=duplicates,invalid=invalid)
        return {"status":"RUNNING" if self.available else "SOURCE_UNAVAILABLE","stored":stored,"duplicates":duplicates,"invalid":invalid}
    def source_status(self): return {"enabled":self.config.pandorick_enabled,"available":self.available,"last_success":self.last_success,"last_error":self.last_error,"statistics":dict(self.stats)}

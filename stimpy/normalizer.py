"""Normalize sanitized Pandorick envelopes into stable Stimpy observations."""
from __future__ import annotations
import hashlib,json
from datetime import UTC,datetime,timedelta
from .models import Observation,SourceType,parse_timestamp,reject_non_finite,utc_now
from .workflow.sanitizer import AuditSanitizer

ENDPOINT_TYPES={"/api/v1/health":SourceType.HEARTBEAT,"/api/v1/system/status":SourceType.SYSTEM,"/api/v1/brain/status":SourceType.BRAIN,"/api/v1/decisions/recent":SourceType.DECISION,"/api/v1/statistics":SourceType.STATISTICS,"/api/v1/warnings":SourceType.ERROR}
class ObservationNormalizer:
    def __init__(self,max_payload_bytes=65536,future_skew_seconds=5):
        self.max_payload_bytes=max_payload_bytes; self.future_skew=timedelta(seconds=future_skew_seconds); self.sanitizer=AuditSanitizer(max_bytes=max_payload_bytes)
    def normalize_envelope(self,endpoint,envelope,limit=100):
        clean_path=endpoint.split("?",1)[0]
        if not isinstance(envelope,dict) or envelope.get("version")!="v1" or "data" not in envelope: raise ValueError("unexpected Pandorick envelope")
        generated=parse_timestamp(envelope.get("generated_at",utc_now()))
        if generated>utc_now()+self.future_skew: raise ValueError("future envelope timestamp")
        data=envelope["data"]
        items=data.get("decisions",[]) if clean_path=="/api/v1/decisions/recent" and isinstance(data,dict) else [data]
        observations=[]; errors=[]
        for item in list(items)[:limit]:
            try: observations.append(self.normalize_item(clean_path,item,generated))
            except (TypeError,ValueError,KeyError) as exc: errors.append(type(exc).__name__)
        return observations,errors
    def normalize_item(self,endpoint,item,generated):
        if not isinstance(item,dict): raise TypeError("item must be object")
        reject_non_finite(item); payload=self.sanitizer.sanitize(item)
        raw=json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False).encode()
        if len(raw)>self.max_payload_bytes: raise ValueError("payload too large")
        digest=hashlib.sha256(raw).hexdigest(); source_type=ENDPOINT_TYPES[endpoint].value
        source_ts=parse_timestamp(item.get("created_at") or item.get("last_update_at") or generated)
        if source_ts>utc_now()+self.future_skew: raise ValueError("future source timestamp")
        event_id=str(item.get("decision_id") or item.get("event_id") or hashlib.sha256((endpoint+digest).encode()).hexdigest())
        correlation=str(item.get("correlation_id") or item.get("decision_id") or event_id)
        oid=hashlib.sha256(f"pandorick|{endpoint}|{event_id}|{digest}".encode()).hexdigest()
        return Observation(oid,event_id,correlation,"pandorick",endpoint,source_type,utc_now(),source_ts,str(item.get("symbol") or "SYSTEM"),str(item.get("market") or item.get("market_type") or "system"),payload,digest,1)

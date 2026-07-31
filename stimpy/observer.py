"""Normalize local prototype payloads without contacting external services."""
from __future__ import annotations
import hashlib,json
from collections.abc import Mapping
from datetime import UTC,datetime
from typing import Any
from .models import Decision,Observation,Outcome,SourceType,parse_timestamp,reject_non_finite

class Observer:
    REQUIRED=("symbol","market","decision","confidence","outcome","profit","source")
    def receive(self,decision:Mapping[str,Any])->Observation:
        if not isinstance(decision,Mapping): raise TypeError("decision payload must be a mapping")
        missing=[key for key in self.REQUIRED if key not in decision]
        if missing: raise ValueError(f"missing required fields: {', '.join(missing)}")
        for key in ("symbol","market","decision","outcome","source"):
            if not isinstance(decision[key],str) or not decision[key].strip(): raise TypeError(f"{key} must be a non-empty string")
        if isinstance(decision["confidence"],bool) or not isinstance(decision["confidence"],(int,float)): raise TypeError("confidence must be numeric")
        if isinstance(decision["profit"],bool) or not isinstance(decision["profit"],(int,float)): raise TypeError("profit must be numeric")
        reject_non_finite(dict(decision)); direction=Decision(decision["decision"].upper()); outcome=Outcome(decision["outcome"].upper())
        confidence=float(decision["confidence"]); profit=float(decision["profit"])
        timestamp=parse_timestamp(decision["timestamp"]) if "timestamp" in decision else datetime.now(UTC)
        canonical={"symbol":decision["symbol"].upper(),"market":decision["market"].lower(),"decision":direction.value,"confidence":confidence,"outcome":outcome.value,"profit":profit,"source":decision["source"].strip()}
        raw=json.dumps(canonical,sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False).encode(); digest=hashlib.sha256(raw).hexdigest()
        observation_id=str(decision.get("observation_id") or hashlib.sha256(b"stimpy-prototype|"+raw).hexdigest())
        payload=dict(canonical); payload["timestamp"]=timestamp.isoformat()
        return Observation(observation_id,observation_id,observation_id,canonical["source"],"local://stimpy/prototype",SourceType.OUTCOME.value,datetime.now(UTC),timestamp,canonical["symbol"],canonical["market"],payload,digest,1,direction.value,confidence,outcome.value,profit)

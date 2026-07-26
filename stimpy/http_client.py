"""Local GET-only HTTP client. No public write operation exists."""
from __future__ import annotations
import json,time,urllib.error,urllib.parse,urllib.request

class ReadOnlyViolationError(RuntimeError): pass
class HttpClientError(RuntimeError): pass
class ReadOnlyHttpClient:
    def __init__(self,base_url,timeout=5,max_retries=2,backoff=2,sleep=time.sleep):
        parsed=urllib.parse.urlparse(base_url)
        if parsed.scheme!="http" or parsed.hostname not in {"127.0.0.1","localhost"}: raise ValueError("only local HTTP sources are allowed")
        self.base_url=base_url.rstrip("/"); self.timeout=timeout; self.max_retries=max_retries; self.backoff=backoff; self._sleep=sleep
    def get(self,path):
        if not path.startswith("/"): raise ValueError("absolute endpoint path required")
        request=urllib.request.Request(self.base_url+path,method="GET",headers={"Accept":"application/json","X-Pandorick-Rick-API":"1","User-Agent":"StimpyBrain/read-only"})
        last=None
        for attempt in range(self.max_retries+1):
            try:
                with urllib.request.urlopen(request,timeout=self.timeout) as response:
                    raw=response.read()
                    return json.loads(raw.decode("utf-8"))
            except (urllib.error.URLError,TimeoutError,json.JSONDecodeError,UnicodeDecodeError) as exc:
                last=exc
                if attempt<self.max_retries: self._sleep(self.backoff*(2**attempt))
        raise HttpClientError(type(last).__name__) from last
    def request(self,method,path):
        if method.upper()!="GET": raise ReadOnlyViolationError("Stimpy HTTP client permits GET only")
        return self.get(path)

"""Local GET-only Stimpy HTTP API with bounded pagination."""
from __future__ import annotations
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from threading import Thread
from urllib.parse import parse_qs,urlparse

class ReadOnlyAPI:
    def __init__(self,store,memory,learning,graph,worker=None): self.store,self.memory,self.learning,self.graph,self.worker=store,memory,learning,graph,worker
    def health(self): return {"status":self.worker.status if self.worker else "STOPPED","database":"OK","read_only":True}
    def status(self): return self.worker.status_snapshot() if self.worker else {"status":"STOPPED","mode":"observe","read_only":True}
    def source_status(self): return self.worker.adapter.source_status() if self.worker else {"enabled":False,"available":None}
    def observations(self,limit=100,offset=0): return {"items":self.store.list(limit,offset),"limit":limit,"offset":offset,"total":self.store.count()}
    def memory_snapshot(self,limit=100,offset=0): return self.memory.snapshot(limit,offset)
    def patterns(self,limit=100): return self.learning.analyze(limit)
    def workflow_results(self,limit=100,offset=0): return {"items":self.store.list_workflow_results(limit,offset),"total":self.store.count("workflow_results")}
    def evidence_results(self,limit=100,offset=0): return {"items":self.store.list_evidence(limit,offset),"limit":limit,"offset":offset,"total":self.store.count("evidence_results")}
    def reasoning_results(self,limit=100,offset=0): return {"items":self.store.list_reasoning(limit,offset),"limit":limit,"offset":offset,"total":self.store.count("reasoning_results")}
    def critic_results(self,limit=100,offset=0): return {"items":self.store.list_critics(limit,offset),"limit":limit,"offset":offset,"total":self.store.count("critic_results")}
    def knowledge_graph(self): return self.graph()
    def statistics(self): return {"observations":self.store.count(),"memories":self.store.count("memories"),"workflow_results":self.store.count("workflow_results"),"evidence_results":self.store.count("evidence_results"),"reasoning_results":self.store.count("reasoning_results"),"critic_results":self.store.count("critic_results")}

ROUTES={"/api/stimpy/health":"health","/api/stimpy/status":"status","/api/stimpy/source-status":"source_status","/api/stimpy/observations/recent":"observations","/api/stimpy/memory":"memory_snapshot","/api/stimpy/evidence/recent":"evidence_results","/api/stimpy/reasoning/recent":"reasoning_results","/api/stimpy/critic/recent":"critic_results","/api/stimpy/patterns":"patterns","/api/stimpy/workflow-results/recent":"workflow_results","/api/stimpy/graph":"knowledge_graph","/api/stimpy/statistics":"statistics"}
class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed=urlparse(self.path); name=ROUTES.get(parsed.path)
        if not name: return self._send({"error":"not found"},HTTPStatus.NOT_FOUND)
        query=parse_qs(parsed.query); limit=max(1,min(int((query.get("limit")or["100"])[0]),100)); offset=max(0,int((query.get("offset")or["0"])[0]))
        fn=getattr(self.server.api,name); kwargs={}
        if name in {"observations","memory_snapshot","workflow_results","evidence_results","reasoning_results","critic_results"}: kwargs={"limit":limit,"offset":offset}
        elif name=="patterns": kwargs={"limit":limit}
        try: self._send(fn(**kwargs))
        except Exception as exc: self._send({"error":type(exc).__name__},HTTPStatus.INTERNAL_SERVER_ERROR)
    def do_POST(self): self._send({"error":"read-only api"},HTTPStatus.METHOD_NOT_ALLOWED)
    do_PUT=do_POST; do_PATCH=do_POST; do_DELETE=do_POST
    def _send(self,payload,status=HTTPStatus.OK):
        body=json.dumps(payload,ensure_ascii=True,default=str).encode(); self.send_response(status); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(body))); self.send_header("Cache-Control","no-store"); self.end_headers(); self.wfile.write(body)
    def log_message(self,*args): pass
class StimpyApiServer:
    def __init__(self,api,host="127.0.0.1",port=8765): self._server=ThreadingHTTPServer((host,port),_Handler); self._server.api=api; self._thread=None
    @property
    def url(self): return f"http://{self._server.server_address[0]}:{self._server.server_address[1]}"
    def start(self): self._thread=Thread(target=self._server.serve_forever,name="stimpy-read-only-api",daemon=True); self._thread.start()
    def stop(self): self._server.shutdown(); self._server.server_close(); self._thread.join(timeout=5) if self._thread else None

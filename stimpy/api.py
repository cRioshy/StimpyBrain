"""Local GET-only Stimpy HTTP API with bounded pagination."""
from __future__ import annotations
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import parse_qs,urlparse

_STATIC_DIR=Path(__file__).with_name("static")
CONTROL_ASSETS={"/controlcenter":("controlcenter.html","text/html; charset=utf-8"),"/controlcenter/":("controlcenter.html","text/html; charset=utf-8"),"/controlcenter/app.css":("controlcenter.css","text/css; charset=utf-8"),"/controlcenter/app.js":("controlcenter.js","text/javascript; charset=utf-8")}

class ReadOnlyAPI:
    def __init__(self,store,memory,learning,graph,worker=None,shitzo_lab=None,shitzo_repository=None,shitzo_collector=None,social_worker=None,social_repository=None,social_config=None,shitzo_regime_analysis=None): self.store,self.memory,self.learning,self.graph,self.worker,self.shitzo_lab,self.shitzo_repository,self.shitzo_collector,self.social_worker,self.social_repository,self.social_config,self.shitzo_regime_analysis=store,memory,learning,graph,worker,shitzo_lab,shitzo_repository,shitzo_collector,social_worker,social_repository,social_config,shitzo_regime_analysis
    def health(self): return {"status":self.worker.status if self.worker else "STOPPED","database":"OK","read_only":True}
    def status(self): return self.worker.status_snapshot() if self.worker else {"status":"STOPPED","mode":"observe","read_only":True}
    def source_status(self): return self.worker.adapter.source_status() if self.worker else {"enabled":False,"available":None}
    def observations(self,limit=100,offset=0): return {"items":self.store.list(limit,offset),"limit":limit,"offset":offset,"total":self.store.count()}
    def memory_snapshot(self,limit=100,offset=0): return self.memory.snapshot(limit,offset)
    def patterns(self,limit=100,offset=0,status=None): return {"items":self.store.list_patterns(limit,offset,status),"limit":limit,"offset":offset,"total":self.store.count("patterns"),"mode":"explicit_evidence_descriptive_only","model_updates":0,"causal_claims":0}
    def workflow_results(self,limit=100,offset=0): return {"items":self.store.list_workflow_results(limit,offset),"total":self.store.count("workflow_results")}
    def evidence_results(self,limit=100,offset=0): return {"items":self.store.list_evidence(limit,offset),"limit":limit,"offset":offset,"total":self.store.count("evidence_results")}
    def reasoning_results(self,limit=100,offset=0): return {"items":self.store.list_reasoning(limit,offset),"limit":limit,"offset":offset,"total":self.store.count("reasoning_results")}
    def critic_results(self,limit=100,offset=0): return {"items":self.store.list_critics(limit,offset),"limit":limit,"offset":offset,"total":self.store.count("critic_results")}
    def incubations(self,limit=100,offset=0,status=None): return {"items":self.store.list_incubations(limit,offset,status),"limit":limit,"offset":offset,"total":self.store.count("incubation_tasks")}
    def hypotheses(self,limit=100,offset=0,status=None): return {"items":self.store.list_hypotheses(limit,offset,status),"limit":limit,"offset":offset,"total":self.store.count("hypotheses"),"causal_claims":0,"predictive_probability":False}
    def hypothesis(self,hypothesis_id): return self.store.get_hypothesis_dict(hypothesis_id)
    def hypothesis_evidence(self,hypothesis_id,limit=100,offset=0): return {"items":self.store.list_hypothesis_evidence(hypothesis_id,limit,offset),"limit":limit,"offset":offset,"total":self.store.count_hypothesis_evidence(hypothesis_id)} if self.store.get_hypothesis(hypothesis_id) else None
    def hypothesis_evaluation(self,hypothesis_id): return self.store.latest_hypothesis_evaluation(hypothesis_id) if self.store.get_hypothesis(hypothesis_id) else None
    def hypothesis_reasoning(self,hypothesis_id): return self.store.latest_hypothesis_reasoning(hypothesis_id) if self.store.get_hypothesis(hypothesis_id) else None
    def hypothesis_critic(self,hypothesis_id): return self.store.latest_hypothesis_critic(hypothesis_id) if self.store.get_hypothesis(hypothesis_id) else None
    def hypothesis_lifecycle(self,hypothesis_id,limit=100,offset=0): return {"items":self.store.list_hypothesis_lifecycle_events(hypothesis_id,limit,offset),"limit":limit,"offset":offset,"total":self.store.count_hypothesis_lifecycle_events(hypothesis_id)} if self.store.get_hypothesis(hypothesis_id) else None
    def hypothesis_incubations(self,limit=100,offset=0,status=None): return {"items":self.store.list_hypothesis_incubations(limit,offset,status),"limit":limit,"offset":offset,"total":self.store.count("hypothesis_incubations")}
    def replay_runs(self,limit=100,offset=0): return {"items":self.store.list_replay_runs(limit,offset),"limit":limit,"offset":offset,"total":self.store.count("replay_runs")}
    def replay_cases(self,run_id,limit=100,offset=0,split=None): return {"items":self.store.list_replay_cases(run_id,limit,offset,split),"limit":limit,"offset":offset} if self.store.get_replay_run(run_id) else None
    def training_runs(self,limit=100,offset=0): return {"items":self.store.list_pandorick_training_runs(limit,offset),"limit":limit,"offset":offset,"total":self.store.count("pandorick_training_runs")}
    def training_metrics(self,run_id,limit=100,offset=0,hypothesis_key=None,split=None): return {"items":self.store.list_pandorick_training_metrics(run_id,limit,offset,hypothesis_key,split),"limit":limit,"offset":offset} if self.store.get_pandorick_training_run(run_id) else None
    def shitzo_status(self):
        status=self.shitzo_lab.status() if self.shitzo_lab else {"enabled":False,"active":False,"automatic":False,"live_provider":False,"real_orders":False,"run":None}
        if self.shitzo_collector: status.update(self.shitzo_collector.snapshot())
        return status
    def shitzo_traders(self): return {"items":[{"trader_id":t.trader_id,"strategy_version":t.rules.strategy_version,"threshold":t.rules.threshold,"max_confidence":t.rules.max_confidence} for t in self.shitzo_lab.traders],"active":self.shitzo_lab.active} if self.shitzo_lab else {"items":[],"active":False}
    def _shitzo_list(self,kind,limit,offset,run_id=None,status=None):
        if not self.shitzo_repository: return {"items":[],"limit":limit,"offset":offset,"total":0}
        fn=getattr(self.shitzo_repository,f"list_{kind}");kwargs={"limit":limit,"offset":offset,"run_id":run_id}
        if kind=="positions": kwargs["status"]=status
        return {"items":fn(**kwargs),"limit":limit,"offset":offset,"total":self.shitzo_repository.count(f"shitzo_{kind}",run_id,status if kind=="positions" else None)}
    def shitzo_accounts(self,limit=100,offset=0,run_id=None): return self._shitzo_list("accounts",limit,offset,run_id)
    def shitzo_positions(self,limit=100,offset=0,run_id=None,status=None): return self._shitzo_list("positions",limit,offset,run_id,status)
    def shitzo_decisions(self,limit=100,offset=0,run_id=None): return self._shitzo_list("decisions",limit,offset,run_id)
    def shitzo_trades(self,limit=100,offset=0,run_id=None): return self._shitzo_list("trades",limit,offset,run_id)
    def shitzo_regimes(self,limit=100,offset=0,run_id=None,symbol=None,regime=None): return {"items":self.shitzo_repository.list_regimes(limit,offset,run_id,symbol,regime),"limit":limit,"offset":offset} if self.shitzo_repository else {"items":[]}
    def shitzo_current_regimes(self,run_id=None): return {"items":self.shitzo_repository.current_regimes(run_id),"descriptive_only":True} if self.shitzo_repository else {"items":[]}
    def shitzo_regime_distribution(self,run_id=None): return {"items":self.shitzo_repository.regime_distribution(run_id),"descriptive_only":True} if self.shitzo_repository else {"items":[]}
    def shitzo_regime_performance(self,run_id=None,trader_id=None,symbol=None): return {"items":self.shitzo_regime_analysis.performance(run_id,trader_id,symbol),"descriptive_only":True,"automatic_parameter_changes":False} if self.shitzo_regime_analysis else {"items":[]}
    def shitzo_regime_losses(self,limit=100,offset=0,run_id=None,trader_id=None,symbol=None): return {"items":self.shitzo_regime_analysis.losses(limit,offset,run_id,trader_id,symbol),"limit":limit,"offset":offset,"descriptive_only":True} if self.shitzo_regime_analysis else {"items":[]}
    def social_status(self):
        base=self.social_worker.snapshot() if self.social_worker else {"status":"DISABLED","enabled":False,"active":False,"read_only":True,"social_writes":False,"trading_signals":False}
        if self.social_repository: base.update({"sources":self.social_repository.source_state(),"counts":self.social_repository.counts(),"queue":self.social_repository.queue_status(1,0)["counts"]})
        return base
    def social_feed(self,limit=100,offset=0,account=None,asset=None,relevance=None,status=None): return {"items":self.social_repository.list_posts(limit,offset,account,asset,relevance,status),"limit":limit,"offset":offset} if self.social_repository else {"items":[],"limit":limit,"offset":offset}
    def social_interesting(self,limit=100,offset=0,account=None,asset=None,status=None):
        items=[]
        if self.social_repository:
            for relevance in ("HIGH_INTEREST","INTERESTING"):
                items.extend(self.social_repository.list_posts(limit,0,account,asset,relevance,status))
        items.sort(key=lambda x:x["published_at"],reverse=True);return {"items":items[offset:offset+limit],"limit":limit,"offset":offset}
    def social_post(self,social_post_id): return self.social_repository.get_post(social_post_id) if self.social_repository else None
    def social_accounts(self): return {"items":self.social_repository.source_state()} if self.social_repository else {"items":[]}
    def social_reactions(self,limit=100,offset=0): return {"items":self.social_repository.list_reactions(limit,offset),"limit":limit,"offset":offset} if self.social_repository else {"items":[]}
    def social_influence(self,limit=100,offset=0): return {"items":self.social_repository.list_profiles(limit,offset),"label":"Historical Influence Association","causal_claims":0,"predictive_probability":False} if self.social_repository else {"items":[]}
    def social_hypotheses(self,limit=100,offset=0): return {"items":self.social_repository.list_suggestions(limit,offset),"automatic_promotion":False} if self.social_repository else {"items":[]}
    def social_sources(self): return {"items":self.social_repository.source_state(),"allowed_types":["RSS","REDDIT"],"x_enabled":False} if self.social_repository else {"items":[]}
    def social_queue(self,limit=100,offset=0):
        payload=self.social_repository.queue_status(limit,offset) if self.social_repository else {"items":[],"counts":{}};payload.update({"limit":limit,"offset":offset});return payload
    def social_history(self,limit=100,offset=0,event_id=None): return {"items":self.social_repository.list_historical_matches(event_id,limit,offset),"limit":limit,"offset":offset,"causal_claims":0,"predictions":False} if self.social_repository else {"items":[]}
    def knowledge_graph(self): return self.graph()
    def statistics(self): return {"observations":self.store.count(),"memories":self.store.count("memories"),"workflow_results":self.store.count("workflow_results"),"evidence_results":self.store.count("evidence_results"),"reasoning_results":self.store.count("reasoning_results"),"critic_results":self.store.count("critic_results"),"incubation_tasks":self.store.count("incubation_tasks"),"patterns":self.store.count("patterns"),"pattern_cases":self.store.count("pattern_cases"),"hypotheses":self.store.count("hypotheses"),"hypothesis_evidence":self.store.count("hypothesis_evidence"),"hypothesis_evaluations":self.store.count("hypothesis_evaluations"),"hypothesis_reasoning":self.store.count("hypothesis_reasoning"),"hypothesis_critics":self.store.count("hypothesis_critics"),"hypothesis_incubations":self.store.count("hypothesis_incubations"),"hypothesis_lifecycle_events":self.store.count("hypothesis_lifecycle_events")}

ROUTES={"/api/stimpy/health":"health","/api/stimpy/status":"status","/api/stimpy/source-status":"source_status","/api/stimpy/observations/recent":"observations","/api/stimpy/memory":"memory_snapshot","/api/stimpy/evidence/recent":"evidence_results","/api/stimpy/reasoning/recent":"reasoning_results","/api/stimpy/critic/recent":"critic_results","/api/stimpy/incubation":"incubations","/api/stimpy/patterns":"patterns","/api/stimpy/hypotheses":"hypotheses","/api/stimpy/hypothesis-incubations":"hypothesis_incubations","/api/stimpy/replay-runs":"replay_runs","/api/stimpy/training-runs":"training_runs","/api/stimpy/shitzo/status":"shitzo_status","/api/stimpy/shitzo/traders":"shitzo_traders","/api/stimpy/shitzo/accounts":"shitzo_accounts","/api/stimpy/shitzo/positions":"shitzo_positions","/api/stimpy/shitzo/decisions":"shitzo_decisions","/api/stimpy/shitzo/trades":"shitzo_trades","/api/stimpy/social/status":"social_status","/api/stimpy/social/feed":"social_feed","/api/stimpy/social/interesting":"social_interesting","/api/stimpy/social/accounts":"social_accounts","/api/stimpy/social/reactions":"social_reactions","/api/stimpy/social/influence":"social_influence","/api/stimpy/social/hypotheses":"social_hypotheses","/api/stimpy/social-lite/status":"social_status","/api/stimpy/social-lite/feed":"social_feed","/api/stimpy/social-lite/interesting":"social_interesting","/api/stimpy/social-lite/reactions":"social_reactions","/api/stimpy/social-lite/history":"social_history","/api/stimpy/social-lite/queue":"social_queue","/api/stimpy/social-lite/sources":"social_sources","/api/stimpy/social-lite/hypotheses":"social_hypotheses","/api/stimpy/workflow-results/recent":"workflow_results","/api/stimpy/graph":"knowledge_graph","/api/stimpy/statistics":"statistics"}
ROUTES.update({"/api/stimpy/shitzo/regimes":"shitzo_regimes","/api/stimpy/shitzo/regimes/current":"shitzo_current_regimes","/api/stimpy/shitzo/regime-distribution":"shitzo_regime_distribution","/api/stimpy/shitzo/regime-performance":"shitzo_regime_performance","/api/stimpy/shitzo/regime-losses":"shitzo_regime_losses"})
class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed=urlparse(self.path); name=ROUTES.get(parsed.path); hypothesis_id=None
        if parsed.path in CONTROL_ASSETS: return self._send_asset(*CONTROL_ASSETS[parsed.path])
        parts=parsed.path.strip("/").split("/")
        run_id=None
        if name is None and len(parts)==5 and parts[:3]==["api","stimpy","replay-runs"] and parts[4]=="cases": run_id=parts[3]; name="replay_cases"
        if name is None and len(parts)==5 and parts[:3]==["api","stimpy","training-runs"] and parts[4]=="metrics": run_id=parts[3]; name="training_metrics"
        if name is None and len(parts)==5 and parts[:4]==["api","stimpy","social","posts"]: social_post_id=parts[4]; name="social_post"
        else: social_post_id=None
        if name is None and len(parts) in {4,5} and parts[:3]==["api","stimpy","hypotheses"]:
            hypothesis_id=parts[3]
            name="hypothesis" if len(parts)==4 else {"evidence":"hypothesis_evidence","evaluation":"hypothesis_evaluation","reasoning":"hypothesis_reasoning","critic":"hypothesis_critic","lifecycle":"hypothesis_lifecycle"}.get(parts[4])
        if not name: return self._send({"error":"not found"},HTTPStatus.NOT_FOUND)
        query=parse_qs(parsed.query); limit=max(1,min(int((query.get("limit")or["100"])[0]),100)); offset=max(0,int((query.get("offset")or["0"])[0]))
        fn=getattr(self.server.api,name); kwargs={}
        if name in {"observations","memory_snapshot","workflow_results","evidence_results","reasoning_results","critic_results"}: kwargs={"limit":limit,"offset":offset}
        elif name=="incubations": kwargs={"limit":limit,"offset":offset,"status":(query.get("status")or[None])[0]}
        elif name=="patterns": kwargs={"limit":limit,"offset":offset,"status":(query.get("status")or[None])[0]}
        elif name=="hypotheses": kwargs={"limit":limit,"offset":offset,"status":(query.get("status")or[None])[0]}
        elif name=="hypothesis": kwargs={"hypothesis_id":hypothesis_id}
        elif name=="hypothesis_evidence": kwargs={"hypothesis_id":hypothesis_id,"limit":limit,"offset":offset}
        elif name=="hypothesis_evaluation": kwargs={"hypothesis_id":hypothesis_id}
        elif name=="hypothesis_reasoning": kwargs={"hypothesis_id":hypothesis_id}
        elif name=="hypothesis_critic": kwargs={"hypothesis_id":hypothesis_id}
        elif name=="hypothesis_lifecycle": kwargs={"hypothesis_id":hypothesis_id,"limit":limit,"offset":offset}
        elif name=="hypothesis_incubations": kwargs={"limit":limit,"offset":offset,"status":(query.get("status")or[None])[0]}
        elif name=="replay_runs": kwargs={"limit":limit,"offset":offset}
        elif name=="replay_cases": kwargs={"run_id":run_id,"limit":limit,"offset":offset,"split":(query.get("split")or[None])[0]}
        elif name=="training_runs": kwargs={"limit":limit,"offset":offset}
        elif name=="training_metrics": kwargs={"run_id":run_id,"limit":limit,"offset":offset,"hypothesis_key":(query.get("hypothesis_key")or[None])[0],"split":(query.get("split")or[None])[0]}
        elif name in {"social_feed","social_interesting"}: kwargs={"limit":limit,"offset":offset,"account":(query.get("account")or[None])[0],"asset":(query.get("asset")or[None])[0],"relevance":(query.get("relevance")or[None])[0],"status":(query.get("status")or[None])[0]} if name=="social_feed" else {"limit":limit,"offset":offset,"account":(query.get("account")or[None])[0],"asset":(query.get("asset")or[None])[0],"status":(query.get("status")or[None])[0]}
        elif name=="social_post": kwargs={"social_post_id":social_post_id}
        elif name in {"social_reactions","social_influence","social_hypotheses"}: kwargs={"limit":limit,"offset":offset}
        elif name=="social_queue": kwargs={"limit":limit,"offset":offset}
        elif name=="social_history": kwargs={"limit":limit,"offset":offset,"event_id":(query.get("event_id")or[None])[0]}
        elif name in {"shitzo_accounts","shitzo_decisions","shitzo_trades"}: kwargs={"limit":limit,"offset":offset,"run_id":(query.get("run_id")or[None])[0]}
        elif name=="shitzo_positions": kwargs={"limit":limit,"offset":offset,"run_id":(query.get("run_id")or[None])[0],"status":(query.get("status")or[None])[0]}
        elif name=="shitzo_regimes": kwargs={"limit":limit,"offset":offset,"run_id":(query.get("run_id")or[None])[0],"symbol":(query.get("symbol")or[None])[0],"regime":(query.get("regime")or[None])[0]}
        elif name in {"shitzo_current_regimes","shitzo_regime_distribution"}: kwargs={"run_id":(query.get("run_id")or[None])[0]}
        elif name=="shitzo_regime_performance": kwargs={"run_id":(query.get("run_id")or[None])[0],"trader_id":(query.get("trader_id")or[None])[0],"symbol":(query.get("symbol")or[None])[0]}
        elif name=="shitzo_regime_losses": kwargs={"limit":limit,"offset":offset,"run_id":(query.get("run_id")or[None])[0],"trader_id":(query.get("trader_id")or[None])[0],"symbol":(query.get("symbol")or[None])[0]}
        try:
            payload=fn(**kwargs)
            if payload is None: return self._send({"error":"not found"},HTTPStatus.NOT_FOUND)
            self._send(payload)
        except Exception as exc: self._send({"error":type(exc).__name__},HTTPStatus.INTERNAL_SERVER_ERROR)
    def do_POST(self): self._send({"error":"read-only api"},HTTPStatus.METHOD_NOT_ALLOWED)
    do_PUT=do_POST; do_PATCH=do_POST; do_DELETE=do_POST
    def _send_asset(self,filename,content_type):
        try: body=(_STATIC_DIR/filename).read_bytes()
        except OSError: return self._send({"error":"not found"},HTTPStatus.NOT_FOUND)
        self.send_response(HTTPStatus.OK); self.send_header("Content-Type",content_type); self.send_header("Content-Length",str(len(body))); self.send_header("Cache-Control","no-store"); self.send_header("Content-Security-Policy","default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"); self.send_header("X-Content-Type-Options","nosniff"); self.end_headers(); self.wfile.write(body)
    def _send(self,payload,status=HTTPStatus.OK):
        body=json.dumps(payload,ensure_ascii=True,default=str).encode(); self.send_response(status); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(body))); self.send_header("Cache-Control","no-store"); self.end_headers(); self.wfile.write(body)
    def log_message(self,*args): pass
class StimpyApiServer:
    def __init__(self,api,host="127.0.0.1",port=8765): self._server=ThreadingHTTPServer((host,port),_Handler); self._server.api=api; self._thread=None
    @property
    def url(self): return f"http://{self._server.server_address[0]}:{self._server.server_address[1]}"
    def start(self): self._thread=Thread(target=self._server.serve_forever,name="stimpy-read-only-api",daemon=True); self._thread.start()
    def stop(self): self._server.shutdown(); self._server.server_close(); self._thread.join(timeout=5) if self._thread else None

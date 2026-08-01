import asyncio,json,sqlite3,tempfile,time,unittest,urllib.error,urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC,datetime,timedelta
from pathlib import Path
from unittest.mock import patch
from stimpy.api import ReadOnlyAPI,StimpyApiServer
from stimpy.config import StimpyConfig
from stimpy.events import InternalEvents
from stimpy.http_client import HttpClientError,ReadOnlyHttpClient,ReadOnlyViolationError
from stimpy.knowledge_graph import build_graph
from stimpy.learning_service import LearningService
from stimpy.memory_service import MemoryService
from stimpy.normalizer import ObservationNormalizer
from stimpy.observation_adapter import ObservationAdapter
from stimpy.observation_store import ObservationStore
from stimpy.worker import StimpyWorker

def envelope(data,stamp=None): return {"status":"ok","source":"pandoriki","version":"v1","generated_at":stamp or datetime.now(UTC).isoformat(),"data":data}
class FakeClient:
    def __init__(self,responses): self.responses=list(responses); self.calls=[]
    def get(self,path):
        self.calls.append(path); value=self.responses.pop(0)
        if isinstance(value,Exception): raise value
        return value
class DummyWorkflow:
    async def evaluate_observation(self,row): return {"id":"w:"+row["observation_id"],"status":"REJECTED","reasons":["shadow"],"gates":["DataQuality"]}
class Response:
    def __init__(self,body): self.body=body
    def __enter__(self): return self
    def __exit__(self,*a): pass
    def read(self): return self.body

class Phase2Tests(unittest.TestCase):
    def setUp(self): self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name); self.store=ObservationStore(self.root/"database"/"x.db",self.root,512); self.norm=ObservationNormalizer(65536,5)
    def tearDown(self):
        try:self.store.close()
        except Exception:pass
        StimpyWorker._active=False; self.temp.cleanup()
    def observation(self,endpoint="/api/v1/decisions/recent",decision="LONG",event="d1",corr=None):
        item={"decision_id":event,"correlation_id":corr or event,"created_at":datetime.now(UTC).isoformat(),"market":"crypto","symbol":"BTCUSDT","direction":decision,"confidence":.7}
        return self.norm.normalize_item(endpoint,item,datetime.now(UTC))
    def test_config_is_disabled_observe_readonly_local(self):
        c=StimpyConfig(); self.assertFalse(c.pandorick_enabled); self.assertEqual(c.mode,"observe"); self.assertTrue(c.read_only); self.assertEqual(c.incubation_default_seconds,3600); self.assertEqual(c.incubation_max_retries,3); c.validate()
        with self.assertRaises(ValueError): replace(c,pandorick_base_url="https://example.com").validate()
    def test_get_only_client_blocks_writes(self):
        c=ReadOnlyHttpClient("http://127.0.0.1:8000")
        for method in ("POST","PUT","PATCH","DELETE"):
            with self.assertRaises(ReadOnlyViolationError): c.request(method,"/api")
    def test_http_get_and_retry(self):
        c=ReadOnlyHttpClient("http://127.0.0.1:8000",max_retries=1,backoff=0)
        with patch("urllib.request.urlopen",side_effect=[urllib.error.URLError("down"),Response(b'{"ok":true}')]) as call: self.assertTrue(c.get("/x")["ok"]); self.assertEqual(call.call_count,2); self.assertEqual(call.call_args.args[0].method,"GET")
    def test_http_invalid_json_isolated(self):
        with patch("urllib.request.urlopen",return_value=Response(b"broken")):
            with self.assertRaises(HttpClientError): ReadOnlyHttpClient("http://localhost:1",max_retries=0).get("/x")
    def test_stable_ids_and_hashes(self):
        item={"decision_id":"x","created_at":"2026-07-26T12:00:00+00:00","symbol":"BTC","market":"crypto","direction":"LONG"}; a=self.norm.normalize_item("/api/v1/decisions/recent",item,datetime.now(UTC)); b=self.norm.normalize_item("/api/v1/decisions/recent",item,datetime.now(UTC)); self.assertEqual(a.observation_id,b.observation_id); self.assertEqual(a.content_hash,b.content_hash)
    def test_secret_redaction(self):
        o=self.norm.normalize_item("/api/v1/system/status",{"token":"secret","status":"ok"},datetime.now(UTC)); self.assertEqual(o.payload["token"],"[REDACTED]")
    def test_future_nan_infinity_and_oversize_rejected(self):
        with self.assertRaises(ValueError): self.norm.normalize_envelope("/api/v1/health",envelope({},(datetime.now(UTC)+timedelta(hours=1)).isoformat()))
        for value in (float("nan"),float("inf")):
            with self.assertRaises(ValueError): self.norm.normalize_item("/api/v1/statistics",{"value":value},datetime.now(UTC))
        with self.assertRaises(ValueError): ObservationNormalizer(100,5).normalize_item("/api/v1/statistics",{"value":"x"*500},datetime.now(UTC))
    def test_mixed_batch_keeps_valid_item(self):
        good={"decision_id":"d","created_at":datetime.now(UTC).isoformat(),"symbol":"BTC","market":"crypto"}; items,errors=self.norm.normalize_envelope("/api/v1/decisions/recent",envelope({"decisions":[good,{"value":float("nan")}] })); self.assertEqual(len(items),1); self.assertEqual(len(errors),1)
    def test_store_jsonl_index_fk_and_rotation(self):
        first=self.observation(event="a"); second=self.observation(event="b")
        self.assertTrue(self.store.append(first)[0]); self.assertTrue(self.store.append(second)[0]); self.assertTrue(self.store.foreign_keys_enabled); self.assertEqual(self.store.schema_version,5); self.assertEqual(self.store.count(),2); self.assertGreaterEqual(len(list((self.root/"observations").glob("*.jsonl"))),2)
    def test_all_deduplication_keys_and_restart(self):
        one=self.observation(event="a",corr="c"); self.assertTrue(self.store.append(one)[0]); self.assertFalse(self.store.append(one)[0])
        duplicate_event=replace(self.observation(event="b"),event_id="a"); self.assertEqual(self.store.append(duplicate_event)[1],"event_id")
        duplicate_corr=self.observation(event="c",corr="c"); self.assertEqual(self.store.append(duplicate_corr)[1],"correlation_id")
        duplicate_content=replace(self.observation(event="d"),content_hash=one.content_hash); self.assertEqual(self.store.append(duplicate_content)[1],"content_hash")
        self.store.close(); self.store=ObservationStore(self.root/"database"/"x.db",self.root,512); self.assertFalse(self.store.append(one)[0])
    def test_parallel_writes(self):
        items=[self.observation(event=f"e{i}") for i in range(20)]
        with ThreadPoolExecutor(max_workers=8) as pool: results=list(pool.map(lambda o:self.store.append(o)[0],items))
        self.assertEqual(sum(results),20)
    def test_incomplete_and_corrupt_jsonl_are_isolated(self):
        p=self.root/"observations"/"bad.jsonl"; p.write_bytes(b'{"ok":1}\nnot-json\n{"partial":')
        valid,corrupt=self.store.validate_jsonl(p); self.assertEqual(len(valid),1); self.assertEqual(corrupt,[2])
    def test_broken_database_fails_closed(self):
        self.store.close(); p=self.root/"bad.db"; p.write_bytes(b"broken")
        with self.assertRaises(sqlite3.DatabaseError): ObservationStore(p,self.root)
    def test_memory_evidence_contradiction_no_causality(self):
        memory=MemoryService(self.store)
        a=self.observation(event="a",decision="LONG"); self.store.append(a); row=self.store.list()[0]; m1=memory.update_from_observation(row); self.assertEqual(m1.evidence_count,1); self.assertEqual(m1.confidence,.25)
        b=self.observation(event="b",decision="LONG",corr="b"); self.store.append(b); m2=memory.update_from_observation(self.store.list()[0]); self.assertEqual(m2.evidence_count,2); self.assertGreater(m2.confidence,m1.confidence)
        c=self.observation(event="c",decision="SHORT",corr="c"); self.store.append(c); m3=memory.update_from_observation(self.store.list()[0]); self.assertGreater(m3.contradiction_count,0); self.assertFalse(m3.content["causal"]); self.assertEqual(LearningService(memory).analyze()["causal_claims"],0)
    def test_adapter_disabled_outage_and_recovery(self):
        events=InternalEvents(); cfg=replace(StimpyConfig(),pandorick_endpoints=("/api/v1/health",)); adapter=ObservationAdapter(cfg,self.store,FakeClient([]),events,self.norm); self.assertEqual(adapter.poll_once()["status"],"DISABLED")
        cfg=replace(cfg,pandorick_enabled=True); client=FakeClient([RuntimeError("down"),envelope({"status":"OK"})]); adapter=ObservationAdapter(cfg,self.store,client,events,self.norm); self.assertEqual(adapter.poll_once()["status"],"SOURCE_UNAVAILABLE"); self.assertEqual(adapter.poll_once()["status"],"RUNNING"); self.assertTrue(any(e["name"]=="STIMPY_SOURCE_RECOVERED" for e in events.recent()))
    def test_readonly_api_and_graph(self):
        memory=MemoryService(self.store); api=ReadOnlyAPI(self.store,memory,LearningService(memory),build_graph); server=StimpyApiServer(api,port=0); server.start()
        try:
            with urllib.request.urlopen(server.url+"/api/stimpy/health",timeout=2) as response: self.assertTrue(json.loads(response.read())["read_only"])
            with self.assertRaises(urllib.error.HTTPError) as ctx: urllib.request.urlopen(urllib.request.Request(server.url+"/api/stimpy/status",method="POST"),timeout=2)
            self.assertEqual(ctx.exception.code,405); graph=json.loads(urllib.request.urlopen(server.url+"/api/stimpy/graph").read()); self.assertEqual(graph["cluster"],"StimpyBrain"); self.assertTrue(any(n["id"]=="pando" for n in graph["nodes"]))
        finally: server.stop()
    def test_worker_single_instance_and_shutdown(self):
        cfg=replace(StimpyConfig(),data_dir=self.root,database_file=self.root/"database"/"x.db",poll_interval_seconds=.05)
        adapter=ObservationAdapter(cfg,self.store,FakeClient([]),InternalEvents(),self.norm); memory=MemoryService(self.store); one=StimpyWorker(cfg,adapter,self.store,memory,DummyWorkflow()); two=StimpyWorker(cfg,adapter,self.store,memory,DummyWorkflow()); one.start();
        with self.assertRaises(RuntimeError): two.start()
        one.stop(); self.assertEqual(one.status,"STOPPED"); self.assertFalse(one._thread.is_alive()); self.assertEqual(json.loads(one.state_file.read_text())["status"],"STOPPED")

if __name__=="__main__": unittest.main()

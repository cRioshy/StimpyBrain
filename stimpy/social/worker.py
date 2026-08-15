"""Independent bounded social polling loop; failures never escape the thread."""
from __future__ import annotations
from datetime import UTC,datetime
from threading import Event,Lock,Thread
from .adapters.x_readonly import SocialAdapterError,SocialRateLimited,XReadOnlyAdapter
from .classifier import SocialClassifier
from .models import EventStatus,SocialInfluenceEvent,SocialPostObservation

class SocialObserverWorker:
    def __init__(self,config,repository,adapter=None,classifier=None):
        self.config=config;self.repository=repository;self.classifier=classifier or SocialClassifier();self.adapter=adapter
        self._stop=Event();self._thread=None;self._lock=Lock();self._status=config.status;self._last_error=None
    def start(self):
        if self.config.status!="READY":self.repository.update_worker_state(self.config.status);return False
        if self._thread and self._thread.is_alive():return False
        self.adapter=self.adapter or XReadOnlyAdapter(self.config.bearer_token,self.config.timeout_seconds,self.config.max_retries)
        self._stop.clear();self._thread=Thread(target=self._run,name="stimpy-social-observer",daemon=True);self._thread.start();return True
    def stop(self):
        self._stop.set()
        if self._thread:self._thread.join(timeout=5)
    def _run(self):
        while not self._stop.is_set():
            self.poll_once();self._stop.wait(self.config.poll_seconds)
    def ingest(self,raw):
        result=self.classifier.classify(raw.text);text=" ".join(raw.text.split())[:self.config.max_text_chars]
        post=SocialPostObservation(raw.platform,raw.account_id,raw.account_handle.lower(),raw.account_display_name,raw.post_id,text,raw.published_at,datetime.now(UTC),raw.language,result.topics,result.assets,result.status,result.relevance_score,result.reasons,result.sentiment,result.sentiment_score,result.intensity_score,raw.engagement or {})
        inserted=self.repository.save_post(post,self.classifier.version)
        if inserted and result.status.value!="IGNORED":self.repository.save_event(SocialInfluenceEvent(post.social_post_id,post.platform,post.account_handle,result.topics[0],result.assets,post.published_at,result.relevance_score,result.sentiment,result.intensity_score,status=EventStatus.NEW))
        return inserted,result.status
    def poll_once(self):
        if self.config.status!="READY":self._status=self.config.status;self.repository.update_worker_state(self._status);return 0
        checked=ignored=interesting=high=0
        try:
            for handle in self.config.accounts:
                for raw in self.adapter.read_public_posts(handle,self.repository.latest_post_id(handle),self.config.max_posts_per_account):
                    inserted,status=self.ingest(raw)
                    if not inserted:continue
                    checked+=1;ignored+=status.value=="IGNORED";interesting+=status.value=="INTERESTING";high+=status.value=="HIGH_INTEREST"
            self._status="OK";self._last_error=None;self.repository.update_worker_state("OK",checked=checked,ignored=ignored,interesting=interesting,high=high)
        except SocialRateLimited as exc:self._status="RATE_LIMITED";self._last_error=str(exc);self.repository.update_worker_state(self._status,self._last_error)
        except (SocialAdapterError,Exception) as exc:self._status="DEGRADED";self._last_error=type(exc).__name__;self.repository.update_worker_state(self._status,self._last_error)
        return checked
    def snapshot(self):return {"status":self._status,"enabled":self.config.enabled,"platform_x_enabled":self.config.platform_x_enabled,"accounts":list(self.config.accounts),"active":bool(self._thread and self._thread.is_alive()),"read_only":True,"social_writes":False,"trading_signals":False,"last_error":self._last_error}

"""Independent RSS/Reddit observer and restart-safe reaction queue."""
from __future__ import annotations
from datetime import UTC,datetime,timedelta
from threading import Event,Thread
from .adapters.reddit_readonly import RedditRateLimited,RedditReadError,RedditReadOnlyAdapter
from .adapters.rss_readonly import FeedReadError,RssReadOnlyAdapter
from .classifier import SocialClassifier
from .market_history import CoinbasePublicCandleFeed
from .models import EventStatus,SocialInfluenceEvent,SocialPostObservation

class SocialMemoryLiteWorker:
    def __init__(self,config,repository,research,rss_adapter=None,reddit_adapter=None,market_feed=None,classifier=None):
        self.config=config;self.repository=repository;self.research=research;self.classifier=classifier or SocialClassifier();self.rss=rss_adapter or RssReadOnlyAdapter(config.timeout_seconds,config.max_retries);self.reddit=reddit_adapter;self.market=market_feed or CoinbasePublicCandleFeed(config.timeout_seconds)
        self._stop=Event();self._thread=None;self._status=config.status;self._last_error=None;self._processing=None;self._polls=0;self._stored=0;self._last_poll_at=None
        self.repository.recover_processing_jobs()
        for source in config.rss_sources:
            self.repository.update_source_state(source.source_id,"RSS",source.display_name,source.status)
        for subreddit in config.subreddits:self.repository.update_source_state(f"reddit-{subreddit.lower()}","REDDIT",f"r/{subreddit}","DISABLED" if not config.reddit_enabled else "READY")
    def start(self):
        if not self.config.enabled:self._status="DISABLED";return False
        if self._thread and self._thread.is_alive():return False
        if self.config.reddit_enabled and self.reddit is None and self.config.reddit_client_id and self.config.reddit_client_secret:self.reddit=RedditReadOnlyAdapter(self.config.reddit_client_id,self.config.reddit_client_secret,self.config.reddit_user_agent,self.config.timeout_seconds,self.config.max_retries)
        self._stop.clear();self._thread=Thread(target=self._run,name="stimpy-social-memory-lite",daemon=True);self._thread.start();return True
    def stop(self):
        self._stop.set()
        if self._thread:self._thread.join(timeout=5)
    def _run(self):
        next_poll=datetime.min.replace(tzinfo=UTC)
        while not self._stop.is_set():
            now=datetime.now(UTC)
            if now>=next_poll:
                self.poll_once();next_poll=now+timedelta(seconds=self.config.poll_seconds)
            self.process_due_jobs(now);self._stop.wait(min(self.config.poll_seconds,30))
    def ingest(self,raw):
        result=self.classifier.classify(raw.text);text=" ".join(raw.text.split())[:self.config.max_text_chars];assets=tuple(x for x in result.assets if x in self.config.assets)
        post=SocialPostObservation(raw.platform,raw.account_id,raw.account_handle.lower(),raw.account_display_name,raw.post_id,text,raw.published_at,datetime.now(UTC),raw.language,result.topics,assets,result.status,result.relevance_score,result.reasons,result.sentiment,result.sentiment_score,result.intensity_score,raw.engagement or {})
        inserted=self.repository.save_post(post,"social-lite-v1")
        if inserted and result.status.value!="IGNORED" and assets:
            event=SocialInfluenceEvent(post.social_post_id,post.platform,post.account_handle,result.topics[0],assets,post.published_at,result.relevance_score,result.sentiment,result.intensity_score,status=EventStatus.NEW)
            if self.repository.save_event(event):self.repository.enqueue_reaction_jobs(event.event_id,assets,post.published_at)
        if inserted:self._stored+=1
        return inserted,result.status
    def poll_once(self):
        if not self.config.enabled:return 0
        stored=0;errors=[]
        if self.config.rss_enabled:
            for source in self.config.rss_sources:
                if not source.url:self.repository.update_source_state(source.source_id,"RSS",source.display_name,source.status);continue
                try:
                    posts=self.rss.read_source(source,self.config.max_items_per_source);added=sum(1 for post in posts if self.ingest(post)[0]);stored+=added;self.repository.update_source_state(source.source_id,"RSS",source.display_name,"OK",seen=len(posts),stored=added)
                except FeedReadError as exc:errors.append(f"{source.source_id}:{exc}");self.repository.update_source_state(source.source_id,"RSS",source.display_name,"DEGRADED",str(exc))
        if self.config.reddit_enabled:
            if not self.reddit:
                for subreddit in self.config.subreddits:self.repository.update_source_state(f"reddit-{subreddit.lower()}","REDDIT",f"r/{subreddit}","DISABLED_NO_CREDENTIALS")
                errors.append("reddit:no credentials")
            else:
                for subreddit in self.config.subreddits:
                    source_id=f"reddit-{subreddit.lower()}"
                    try:
                        posts=self.reddit.read_subreddit(subreddit,limit=self.config.max_items_per_source);added=sum(1 for post in posts if self.ingest(post)[0]);stored+=added;self.repository.update_source_state(source_id,"REDDIT",f"r/{subreddit}","OK",seen=len(posts),stored=added)
                    except RedditRateLimited as exc:errors.append(f"{source_id}:rate limited");self.repository.update_source_state(source_id,"REDDIT",f"r/{subreddit}","RATE_LIMITED",str(exc))
                    except RedditReadError as exc:errors.append(f"{source_id}:{exc}");self.repository.update_source_state(source_id,"REDDIT",f"r/{subreddit}","DEGRADED",str(exc))
        self._polls+=1;self._last_poll_at=datetime.now(UTC).isoformat();self._status="DEGRADED" if errors else "OK";self._last_error="; ".join(errors)[:500] if errors else None;return stored
    def process_due_jobs(self,now=None,limit=25):
        completed=0
        for job in self.repository.claim_due_jobs(now,limit):
            self._processing=job["job_id"]
            try:
                target=datetime.fromisoformat(job["due_at"]);point=self.market.read_at(job["asset_symbol"],target);analysis=self.research.record_market_snapshot(job["event_id"],job["asset_symbol"],job["window_label"],point.price,point.timestamp,point.source,point.volume,point.volatility,"UNKNOWN");self.repository.finish_job(job["job_id"],True);completed+=1
                if analysis.analysis_status=="COMPLETED":self.repository.refresh_historical_matches(job["event_id"],job["asset_symbol"])
            except Exception as exc:self.repository.finish_job(job["job_id"],False,type(exc).__name__)
            finally:self._processing=None
        return completed
    def snapshot(self):
        queue=self.repository.queue_status(1,0);return {"status":self._status,"enabled":self.config.enabled,"rss_enabled":self.config.rss_enabled,"reddit_enabled":self.config.reddit_enabled,"active":bool(self._thread and self._thread.is_alive()),"read_only":True,"social_writes":False,"trading_signals":False,"x_enabled":False,"polls":self._polls,"stored":self._stored,"last_poll_at":self._last_poll_at,"currently_processing":self._processing,"queue_counts":queue["counts"],"last_error":self._last_error}

import io,json,tempfile,unittest,urllib.error,urllib.request
from datetime import UTC,datetime,timedelta
from email.message import Message
from pathlib import Path

from stimpy.api import ReadOnlyAPI,StimpyApiServer
from stimpy.knowledge_graph import build_graph
from stimpy.learning_service import LearningService
from stimpy.memory_service import MemoryService
from stimpy.observation_store import ObservationStore
from stimpy.social.adapters.base import PublicSocialPost
from stimpy.social.adapters.reddit_readonly import RedditReadOnlyAdapter
from stimpy.social.adapters.rss_readonly import RssReadOnlyAdapter
from stimpy.social.lite_config import RssSource,SocialMemoryLiteConfig
from stimpy.social.lite_worker import SocialMemoryLiteWorker
from stimpy.social.market_history import MarketPoint
from stimpy.social.research import SocialResearchService
from stimpy.social.repository import SocialRepository

NOW=datetime(2026,8,14,12,0,tzinfo=UTC)

class Response(io.BytesIO):
    def __init__(self,data,headers=None):super().__init__(data);self.headers=Message();[self.headers.__setitem__(k,v) for k,v in (headers or {}).items()]
    def __enter__(self):return self
    def __exit__(self,*args):self.close()

class SourceFixture:
    def __init__(self,posts):self.posts=posts
    def read_source(self,source,limit=25):return tuple(self.posts[:limit])

class RedditFixture:
    def __init__(self,posts):self.posts=posts
    def read_subreddit(self,subreddit,limit=25):return tuple(self.posts[:limit])

class MarketFixture:
    def read_at(self,asset,at):
        minutes=int((at-NOW).total_seconds()/60);return MarketPoint(100+minutes/100,1000+minutes,.01,at,"fixture-public-candles")

class SocialMemoryLiteTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.db=self.root/"database"/"stimpy.sqlite3";self.store=ObservationStore(self.db,self.root);self.repo=SocialRepository(self.db);self.config=SocialMemoryLiteConfig(True,True,True,60,rss_sources=(RssSource("fixture","Fixture","https://example.invalid/feed"),));self.research=SocialResearchService(self.repo,1)
    def tearDown(self):self.repo.close();self.store.close();self.temp.cleanup()
    def raw(self,post_id="1",text="Bitcoin ETF approval gains momentum",platform="rss",handle="fixture",published=NOW):return PublicSocialPost(platform,handle,handle,handle,post_id,text,published,"en",{})
    def worker(self,posts=()):return SocialMemoryLiteWorker(self.config,self.repo,self.research,SourceFixture(posts),RedditFixture(()),MarketFixture())

    def test_rss_parser_is_bounded_and_does_not_fetch_articles(self):
        xml=b"<rss><channel><item><guid>one</guid><title>Bitcoin ETF update</title><description>BTC volume rises</description><link>https://news.invalid/a</link><pubDate>Fri, 14 Aug 2026 12:00:00 GMT</pubDate></item></channel></rss>";calls=[]
        def opener(request,timeout):calls.append((request.full_url,request.method));return Response(xml,{"ETag":"fixture"})
        items=RssReadOnlyAdapter(opener=opener).read_source(RssSource("test","Test",calls and None or "https://feed.invalid/rss"),1)
        self.assertEqual(1,len(items));self.assertEqual([("https://feed.invalid/rss","GET")],calls);self.assertIn("Bitcoin",items[0].text)

    def test_reddit_uses_oauth_then_gets_public_listing(self):
        calls=[]
        def opener(request,timeout):
            calls.append((request.full_url,request.method))
            if "access_token" in request.full_url:return Response(json.dumps({"access_token":"t","expires_in":3600}).encode())
            payload={"data":{"children":[{"data":{"name":"t3_1","title":"Ethereum update","selftext":"ETH volume","created_utc":NOW.timestamp(),"subreddit_id":"t5_eth","permalink":"/r/Ethereum/1"}}]}};return Response(json.dumps(payload).encode())
        items=RedditReadOnlyAdapter("id","secret","test-agent",opener=opener).read_subreddit("Ethereum",limit=1)
        self.assertEqual(["POST","GET"],[x[1] for x in calls]);self.assertEqual("reddit",items[0].platform);self.assertEqual("ethereum",items[0].account_handle)

    def test_poll_is_idempotent_filters_assets_and_enqueues_all_windows(self):
        worker=self.worker((self.raw(),self.raw("2","DOGE adoption rises")))
        self.assertEqual(2,worker.poll_once());self.assertEqual(0,worker.poll_once());self.assertEqual(2,self.repo.counts()["posts"]);self.assertEqual(5,len(self.repo.queue_status()["items"]));self.assertEqual({"BTC"},set(x["asset_symbol"] for x in self.repo.queue_status()["items"]))

    def test_queue_reaction_history_and_restart_recovery(self):
        worker=self.worker();worker.ingest(self.raw("1"));worker.process_due_jobs(NOW+timedelta(days=2));first=self.repo.list_posts()[0]["event_id"];self.assertEqual("COMPLETED",self.repo.event(first)["status"])
        worker.ingest(self.raw("2","Bitcoin ETF approval and BTC volume rise",published=NOW+timedelta(minutes=1)));worker.process_due_jobs(NOW+timedelta(days=2));second=self.repo.list_posts()[0]["event_id"]
        self.assertTrue(self.repo.list_historical_matches(second));self.assertEqual(10,self.repo.queue_status()["counts"]["COMPLETED"])
        job=self.repo._db.execute("SELECT job_id FROM social_reaction_jobs LIMIT 1").fetchone()[0];self.repo._db.execute("UPDATE social_reaction_jobs SET status='PROCESSING' WHERE job_id=?",(job,));self.repo._db.commit();self.repo.close();self.repo=SocialRepository(self.db);self.assertEqual(1,self.repo.recover_processing_jobs());self.assertEqual("FAILED_RETRYABLE",self.repo._db.execute("SELECT status FROM social_reaction_jobs WHERE job_id=?",(job,)).fetchone()[0])

    def test_read_only_api_and_controlcenter_contract(self):
        worker=self.worker((self.raw(),));worker.poll_once();memory=MemoryService(self.store);api=ReadOnlyAPI(self.store,memory,LearningService(memory),build_graph,social_worker=worker,social_repository=self.repo,social_config=self.config);server=StimpyApiServer(api,port=0);server.start()
        try:
            for endpoint in ("status","feed","interesting","reactions","history","queue","sources","hypotheses"):
                response=urllib.request.urlopen(f"{server.url}/api/stimpy/social-lite/{endpoint}",timeout=2);self.assertEqual(200,response.status);self.assertIsInstance(json.load(response),dict)
            request=urllib.request.Request(server.url+"/api/stimpy/social-lite/feed",data=b"{}",method="POST")
            with self.assertRaises(urllib.error.HTTPError) as caught:urllib.request.urlopen(request,timeout=2)
            self.assertEqual(405,caught.exception.code)
        finally:server.stop()
        script=(Path(__file__).parents[1]/"stimpy"/"static"/"controlcenter.js").read_text(encoding="utf-8")
        for label in ("INTERESSANTE EREIGNISSE","MARKTREAKTIONEN","HISTORISCHE TREFFER","AKTUELL IN VERARBEITUNG","QUEUE-STATUS"):self.assertIn(label,script)
        self.assertNotIn("api.twitter.com",script)

if __name__=="__main__":unittest.main()

import ast,json,tempfile,unittest,urllib.error,urllib.request
from dataclasses import replace
from datetime import UTC,datetime
from pathlib import Path
from stimpy.api import ReadOnlyAPI,StimpyApiServer
from stimpy.knowledge_graph import build_graph
from stimpy.learning_service import LearningService
from stimpy.memory_service import MemoryService
from stimpy.observation_store import ObservationStore
from stimpy.social.adapters.base import PublicSocialPost
from stimpy.social.classifier import SocialClassifier
from stimpy.social.config import SocialConfig
from stimpy.social.models import RelevanceStatus,SocialPostObservation
from stimpy.social.reaction import ReactionAnalyzer
from stimpy.social.research import SocialResearchService
from stimpy.social.repository import SocialRepository
from stimpy.social.worker import SocialObserverWorker

NOW=datetime(2026,8,15,16,0,tzinfo=UTC)
class FixtureAdapter:
    def __init__(self,posts=()):self.posts=posts;self.calls=[]
    def read_public_posts(self,handle,since_id=None,limit=25):self.calls.append((handle,since_id,limit));return tuple(self.posts[:limit])
class SocialIntelligenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.db=self.root/"database"/"stimpy.sqlite3";self.store=ObservationStore(self.db,self.root);self.repo=SocialRepository(self.db);self.classifier=SocialClassifier()
    def tearDown(self):self.repo.close();self.store.close();self.temp.cleanup()
    def raw(self,post_id="1",text="Bitcoin ETF approval is strong"):return PublicSocialPost("x","account-1","research_account","Research Account",post_id,text,NOW,"en",{"like_count":10})
    def test_models_validate_limits_timestamps_and_scores(self):
        result=self.classifier.classify("BTC is strong");post=SocialPostObservation("x","a","handle","Name","1"," BTC   is strong ",NOW,relevance_status=result.status,relevance_score=result.relevance_score)
        self.assertEqual("BTC is strong",post.post_text);self.assertTrue(post.social_post_id.startswith("social-"))
        with self.assertRaises(ValueError):replace(post,relevance_score=float("nan"))
        with self.assertRaises(ValueError):replace(post,post_text="x"*4001)
        with self.assertRaises(ValueError):replace(post,published_at=datetime(2026,1,1))
    def test_relevance_mapping_sentiment_and_irrelevant(self):
        cases={"Bitcoin is strong":("BTC","POSITIVE"),"Ethereum hack":("ETH","NEGATIVE"),"XRP update":("XRP","NEUTRAL"),"DOGE adoption":("DOGE","POSITIVE"),"New crypto regulation":("REGULATION","NEUTRAL"),"The Fed changes interest rate":("MACRO","NEUTRAL")}
        for text,(topic,sentiment) in cases.items():result=self.classifier.classify(text);self.assertIn(topic,result.topics);self.assertEqual(sentiment,result.sentiment.value)
        ignored=self.classifier.classify("Nice weather today");self.assertEqual(RelevanceStatus.IGNORED,ignored.status);self.assertEqual(("UNKNOWN",),ignored.topics);self.assertEqual("MIXED",self.classifier.classify("Bitcoin strong but crash risk").sentiment.value)
    def test_ingest_is_idempotent_and_ignored_creates_no_event(self):
        config=SocialConfig(True,True,("research_account",),"fixture-token",max_text_chars=1000);worker=SocialObserverWorker(config,self.repo,FixtureAdapter(),self.classifier)
        inserted,status=worker.ingest(self.raw());self.assertTrue(inserted);self.assertNotEqual("IGNORED",status.value);duplicate,_=worker.ingest(self.raw());self.assertFalse(duplicate)
        worker.ingest(self.raw("2","Nice weather today"));self.assertEqual(2,len(self.repo.list_posts()));self.assertEqual(1,self.repo.counts()["ignored"]);self.assertEqual(1,self.repo.counts()["tracking"]);self.assertEqual([],self.repo.list_suggestions())
    def test_missing_credentials_and_bounded_fixture_poll(self):
        disabled=SocialObserverWorker(SocialConfig(True,True,("research_account",),""),self.repo);self.assertFalse(disabled.start());self.assertEqual("DISABLED_NO_CREDENTIALS",disabled.snapshot()["status"])
        adapter=FixtureAdapter((self.raw(),self.raw("2","Lunch today")));worker=SocialObserverWorker(SocialConfig(True,True,("research_account",),"fixture",max_posts_per_account=1),self.repo,adapter);self.assertEqual(1,worker.poll_once());self.assertEqual(1,adapter.calls[0][2]);self.assertEqual("OK",worker.snapshot()["status"])
    def test_reaction_windows_baseline_and_lookahead_are_descriptive(self):
        analyzer=ReactionAnalyzer();first=analyzer.analyze("e","BTC",{"T-30m":100,"T0":101,"+5m":102});later=analyzer.analyze("e","BTC",{"T-30m":100,"T0":101,"+5m":102,"+30m":103,"+2h":99,"+24h":104})
        self.assertAlmostEqual(first.pre_event_return,1);self.assertEqual("TRACKING",first.analysis_status);self.assertEqual("COMPLETED",later.analysis_status);self.assertTrue(later.market_was_already_moving);self.assertEqual(first.social_event_id,later.social_event_id);self.assertNotIn("LONG",json.dumps(later.__dict__,default=str));self.assertNotIn("SHORT",json.dumps(later.__dict__,default=str))
    def test_all_reaction_windows_are_restart_safe_and_create_only_candidate(self):
        worker=SocialObserverWorker(SocialConfig(True,True,("research_account",),"fixture"),self.repo,FixtureAdapter());worker.ingest(self.raw());event_id=self.repo.list_posts()[0]["event_id"];service=SocialResearchService(self.repo,1)
        labels=("T-30m","T-5m","T0","+5m","+30m","+2h","+24h")
        for index,label in enumerate(labels):analysis=service.record_market_snapshot(event_id,"BTC",label,100+index,NOW,"fixture",1000+index,0.01,"UP")
        self.assertEqual("COMPLETED",analysis.analysis_status);self.assertEqual(7,len(self.repo.snapshots(event_id,"BTC")));self.assertEqual(1,len(self.repo.list_profiles()));suggestion=self.repo.list_suggestions()[0];self.assertEqual("NEW",suggestion["status"]);self.assertIn("möglicherweise",suggestion["statement"])
    def test_restart_foreign_keys_filters_get_only_and_detail(self):
        worker=SocialObserverWorker(SocialConfig(True,True,("research_account",),"fixture"),self.repo,FixtureAdapter());worker.ingest(self.raw());self.assertTrue(self.repo.foreign_keys_enabled)
        memory=MemoryService(self.store);api=ReadOnlyAPI(self.store,memory,LearningService(memory),build_graph,social_worker=worker,social_repository=self.repo,social_config=worker.config);server=StimpyApiServer(api,port=0);server.start()
        try:
            for endpoint in ("status","feed?asset=BTC","interesting","accounts","reactions","influence","hypotheses"):response=urllib.request.urlopen(f"{server.url}/api/stimpy/social/{endpoint}",timeout=2);self.assertEqual(200,response.status);self.assertIsInstance(json.load(response),dict)
            post=self.repo.list_posts()[0];detail=json.load(urllib.request.urlopen(f"{server.url}/api/stimpy/social/posts/{post['social_post_id']}",timeout=2));self.assertEqual(post["post_id"],detail["post_id"])
            request=urllib.request.Request(server.url+"/api/stimpy/social/feed",data=b"{}",method="POST")
            with self.assertRaises(urllib.error.HTTPError) as caught:urllib.request.urlopen(request,timeout=2)
            self.assertEqual(405,caught.exception.code)
        finally:server.stop()
        self.repo.close();self.repo=SocialRepository(self.db);self.assertEqual(1,len(self.repo.list_posts()))
    def test_package_has_no_external_write_capabilities(self):
        root=Path(__file__).parents[1]/"stimpy"/"social";source="\n".join(p.read_text(encoding="utf-8") for p in root.rglob("*.py"));tree=ast.parse(source);banned={"place_order","create_order","send_message","post_tweet","like","follow","transfer"};calls={node.func.attr for node in ast.walk(tree) if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute)}
        self.assertTrue(banned.isdisjoint(calls));self.assertNotIn("telegram",source.casefold());self.assertNotIn("pandorick",source.casefold())
if __name__=="__main__":unittest.main()

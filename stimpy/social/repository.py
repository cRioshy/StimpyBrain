"""Restart-safe Social storage in Stimpy's existing SQLite database."""
from __future__ import annotations
import json,sqlite3
from datetime import UTC,datetime
from pathlib import Path
from threading import RLock
from .models import SocialInfluenceEvent,SocialPostObservation,SocialReactionAnalysis
from .models import stable_id

SOCIAL_SCHEMA="""
CREATE TABLE IF NOT EXISTS social_posts(
 social_post_id TEXT PRIMARY KEY,platform TEXT NOT NULL,account_id TEXT NOT NULL,account_handle TEXT NOT NULL,account_display_name TEXT NOT NULL,
 post_id TEXT NOT NULL,post_text TEXT NOT NULL,post_text_hash TEXT NOT NULL,published_at TEXT NOT NULL,collected_at TEXT NOT NULL,language TEXT NOT NULL,
 topic_tags TEXT NOT NULL,asset_symbols TEXT NOT NULL,relevance_status TEXT NOT NULL CHECK(relevance_status IN ('IGNORED','WATCH','INTERESTING','HIGH_INTEREST','UNKNOWN')),
 relevance_score REAL NOT NULL,relevance_reasons TEXT NOT NULL,sentiment_label TEXT NOT NULL,sentiment_score REAL NOT NULL,intensity_score REAL NOT NULL,
 engagement_snapshot TEXT NOT NULL,duplicate_group_id TEXT NOT NULL,spam_probability REAL NOT NULL,source_quality REAL NOT NULL,classifier_version TEXT NOT NULL,schema_version INTEGER NOT NULL,
 UNIQUE(platform,post_id));
CREATE INDEX IF NOT EXISTS ix_social_posts_time ON social_posts(published_at DESC);
CREATE INDEX IF NOT EXISTS ix_social_posts_account_time ON social_posts(account_handle,published_at DESC);
CREATE INDEX IF NOT EXISTS ix_social_posts_relevance_time ON social_posts(relevance_status,published_at DESC);
CREATE INDEX IF NOT EXISTS ix_social_posts_text_hash ON social_posts(post_text_hash);
CREATE TABLE IF NOT EXISTS social_events(
 event_id TEXT PRIMARY KEY,social_post_id TEXT NOT NULL UNIQUE,platform TEXT NOT NULL,account_handle TEXT NOT NULL,primary_topic TEXT NOT NULL,
 asset_symbols TEXT NOT NULL,published_at TEXT NOT NULL,relevance_score REAL NOT NULL,sentiment_label TEXT NOT NULL,intensity_score REAL NOT NULL,
 market_snapshot_t0_id TEXT,status TEXT NOT NULL CHECK(status IN ('NEW','TRACKING','COMPLETED','IGNORED','FAILED')),schema_version INTEGER NOT NULL,
 FOREIGN KEY(social_post_id) REFERENCES social_posts(social_post_id));
CREATE INDEX IF NOT EXISTS ix_social_events_status_time ON social_events(status,published_at DESC);
CREATE TABLE IF NOT EXISTS social_market_snapshots(
 snapshot_id TEXT PRIMARY KEY,event_id TEXT NOT NULL,asset_symbol TEXT NOT NULL,window_label TEXT NOT NULL,price REAL NOT NULL,volume REAL,
 volatility REAL,market_regime TEXT NOT NULL,snapshot_at TEXT NOT NULL,source TEXT NOT NULL,created_at TEXT NOT NULL,schema_version INTEGER NOT NULL,
 UNIQUE(event_id,asset_symbol,window_label),FOREIGN KEY(event_id) REFERENCES social_events(event_id));
CREATE INDEX IF NOT EXISTS ix_social_snapshots_event_asset ON social_market_snapshots(event_id,asset_symbol,snapshot_at);
CREATE TABLE IF NOT EXISTS social_reaction_results(
 analysis_id TEXT PRIMARY KEY,social_event_id TEXT NOT NULL,asset_symbol TEXT NOT NULL,pre_event_return REAL,post_5m_return REAL,post_30m_return REAL,
 post_2h_return REAL,post_24h_return REAL,volume_change REAL,volatility_change REAL,reaction_strength REAL NOT NULL,reaction_direction TEXT NOT NULL,
 baseline_adjusted_reaction REAL,market_was_already_moving INTEGER NOT NULL,confidence REAL NOT NULL,analysis_status TEXT NOT NULL,updated_at TEXT NOT NULL,schema_version INTEGER NOT NULL,
 UNIQUE(social_event_id,asset_symbol),FOREIGN KEY(social_event_id) REFERENCES social_events(event_id));
CREATE TABLE IF NOT EXISTS social_account_profiles(
 profile_id TEXT PRIMARY KEY,account_handle TEXT NOT NULL,asset_symbol TEXT NOT NULL,case_count INTEGER NOT NULL,strong_reactions INTEGER NOT NULL,
 no_reactions INTEGER NOT NULL,counter_reactions INTEGER NOT NULL,association_label TEXT NOT NULL,confidence_label TEXT NOT NULL,updated_at TEXT NOT NULL,schema_version INTEGER NOT NULL,
 UNIQUE(account_handle,asset_symbol));
CREATE TABLE IF NOT EXISTS social_hypothesis_links(
 suggestion_id TEXT PRIMARY KEY,account_handle TEXT NOT NULL,asset_symbol TEXT NOT NULL,statement TEXT NOT NULL,status TEXT NOT NULL CHECK(status IN ('NEW','READY_FOR_REVIEW','REJECTED')),
 case_count INTEGER NOT NULL,source_analysis_ids TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,schema_version INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS social_worker_state(
 platform TEXT PRIMARY KEY,status TEXT NOT NULL,last_poll_at TEXT,last_success_at TEXT,last_error TEXT,posts_checked INTEGER NOT NULL,ignored INTEGER NOT NULL,
 interesting INTEGER NOT NULL,high_interest INTEGER NOT NULL,rate_limit_resets INTEGER NOT NULL,updated_at TEXT NOT NULL,schema_version INTEGER NOT NULL);
"""

def _decode(row):
    if not row:return None
    item=dict(row)
    for key in ("topic_tags","asset_symbols","relevance_reasons","engagement_snapshot","source_analysis_ids"):
        if key in item:
            try:item[key]=json.loads(item[key])
            except (TypeError,json.JSONDecodeError):item[key]=[] if key!="engagement_snapshot" else {}
    if "market_was_already_moving" in item:item["market_was_already_moving"]=bool(item["market_was_already_moving"])
    return item

class SocialRepository:
    def __init__(self,database_path,connection=None,lock=None):
        self.path=Path(database_path);self._owns_connection=connection is None;self._lock=lock or RLock();self._db=connection or sqlite3.connect(self.path,check_same_thread=False);self._db.row_factory=sqlite3.Row
        with self._db:
            self._db.execute("PRAGMA foreign_keys=ON");self._db.executescript(SOCIAL_SCHEMA)
            self._db.execute("INSERT OR IGNORE INTO stimpy_schema_migrations VALUES(?,?)",(14,datetime.now(UTC).isoformat()))
    def close(self):
        if self._owns_connection:self._db.close()
    @property
    def foreign_keys_enabled(self):return bool(self._db.execute("PRAGMA foreign_keys").fetchone()[0])
    def save_post(self,p:SocialPostObservation,classifier_version="social-v1"):
        values=(p.social_post_id,p.platform,p.account_id,p.account_handle,p.account_display_name,p.post_id,p.post_text,p.post_text_hash,p.published_at.isoformat(),p.collected_at.isoformat(),p.language,json.dumps(p.topic_tags),json.dumps(p.asset_symbols),p.relevance_status.value,p.relevance_score,json.dumps(p.relevance_reasons),p.sentiment_label.value,p.sentiment_score,p.intensity_score,json.dumps(p.engagement_snapshot,sort_keys=True),p.duplicate_group_id,p.spam_probability,p.source_quality,classifier_version,p.schema_version)
        with self._lock,self._db:
            cur=self._db.execute("INSERT OR IGNORE INTO social_posts VALUES("+",".join("?"*25)+")",values)
            return cur.rowcount==1
    def save_event(self,e:SocialInfluenceEvent):
        with self._lock,self._db:
            cur=self._db.execute("INSERT OR IGNORE INTO social_events VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",(e.event_id,e.social_post_id,e.platform,e.account_handle,e.primary_topic,json.dumps(e.asset_symbols),e.published_at.isoformat(),e.relevance_score,e.sentiment_label.value,e.intensity_score,e.market_snapshot_t0_id,e.status.value,e.schema_version));return cur.rowcount==1
    def save_snapshot(self,event_id,asset,window_label,price,volume,volatility,regime,snapshot_at,source,snapshot_id):
        with self._lock,self._db:self._db.execute("INSERT OR IGNORE INTO social_market_snapshots VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(snapshot_id,event_id,asset,window_label,float(price),volume,volatility,regime,snapshot_at.isoformat(),source,datetime.now(UTC).isoformat(),1))
    def event(self,event_id):return _decode(self._db.execute("SELECT * FROM social_events WHERE event_id=?",(event_id,)).fetchone())
    def snapshots(self,event_id,asset):return [_decode(r) for r in self._db.execute("SELECT * FROM social_market_snapshots WHERE event_id=? AND asset_symbol=? ORDER BY snapshot_at",(event_id,asset)).fetchall()]
    def set_event_status(self,event_id,status):
        with self._lock,self._db:self._db.execute("UPDATE social_events SET status=? WHERE event_id=?",(status,event_id))
    def save_analysis(self,a:SocialReactionAnalysis):
        values=(a.analysis_id,a.social_event_id,a.asset_symbol,a.pre_event_return,a.post_5m_return,a.post_30m_return,a.post_2h_return,a.post_24h_return,a.volume_change,a.volatility_change,a.reaction_strength,a.reaction_direction.value,a.baseline_adjusted_reaction,int(a.market_was_already_moving),a.confidence,a.analysis_status,datetime.now(UTC).isoformat(),a.schema_version)
        with self._lock,self._db:self._db.execute("INSERT INTO social_reaction_results VALUES("+",".join("?"*18)+") ON CONFLICT(analysis_id) DO UPDATE SET post_5m_return=excluded.post_5m_return,post_30m_return=excluded.post_30m_return,post_2h_return=excluded.post_2h_return,post_24h_return=excluded.post_24h_return,volume_change=excluded.volume_change,volatility_change=excluded.volatility_change,reaction_strength=excluded.reaction_strength,reaction_direction=excluded.reaction_direction,baseline_adjusted_reaction=excluded.baseline_adjusted_reaction,market_was_already_moving=excluded.market_was_already_moving,confidence=excluded.confidence,analysis_status=excluded.analysis_status,updated_at=excluded.updated_at",values)
    def list_posts(self,limit=100,offset=0,account=None,asset=None,relevance=None,status=None):
        clauses=[];args=[]
        if account:clauses.append("p.account_handle=?");args.append(account.lstrip("@").lower())
        if asset:clauses.append("p.asset_symbols LIKE ?");args.append(f'%"{asset.upper()}"%')
        if relevance:clauses.append("p.relevance_status=?");args.append(relevance.upper())
        if status:clauses.append("COALESCE(e.status,'IGNORED')=?");args.append(status.upper())
        where=" WHERE "+" AND ".join(clauses) if clauses else ""
        sql="SELECT p.*,e.event_id,e.status AS event_status FROM social_posts p LEFT JOIN social_events e ON e.social_post_id=p.social_post_id"+where+" ORDER BY p.published_at DESC LIMIT ? OFFSET ?"
        args.extend((max(1,min(int(limit),100)),max(0,int(offset))))
        return [_decode(r) for r in self._db.execute(sql,args).fetchall()]
    def get_post(self,social_post_id):
        row=self._db.execute("SELECT p.*,e.event_id,e.status AS event_status FROM social_posts p LEFT JOIN social_events e ON e.social_post_id=p.social_post_id WHERE p.social_post_id=?",(social_post_id,)).fetchone()
        if not row:return None
        item=_decode(row);item["snapshots"]=[_decode(r) for r in self._db.execute("SELECT * FROM social_market_snapshots WHERE event_id=? ORDER BY snapshot_at",(item.get("event_id"),)).fetchall()];item["reactions"]=[_decode(r) for r in self._db.execute("SELECT * FROM social_reaction_results WHERE social_event_id=?",(item.get("event_id"),)).fetchall()];return item
    def list_accounts(self,configured=()):
        stats={r["account_handle"]:dict(r) for r in self._db.execute("SELECT account_handle,COUNT(*) posts,MAX(published_at) last_post,SUM(CASE WHEN relevance_status IN ('INTERESTING','HIGH_INTEREST') THEN 1 ELSE 0 END) relevant_posts FROM social_posts GROUP BY account_handle")}
        return [{"account_handle":h,"status":"ACTIVE","last_post":stats.get(h,{}).get("last_post"),"posts":stats.get(h,{}).get("posts",0),"relevant_posts":stats.get(h,{}).get("relevant_posts",0)} for h in configured]
    def list_reactions(self,limit=100,offset=0):return [_decode(r) for r in self._db.execute("SELECT * FROM social_reaction_results ORDER BY updated_at DESC LIMIT ? OFFSET ?",(max(1,min(limit,100)),max(0,offset))).fetchall()]
    def list_profiles(self,limit=100,offset=0):return [_decode(r) for r in self._db.execute("SELECT * FROM social_account_profiles ORDER BY case_count DESC LIMIT ? OFFSET ?",(max(1,min(limit,100)),max(0,offset))).fetchall()]
    def list_suggestions(self,limit=100,offset=0):return [_decode(r) for r in self._db.execute("SELECT * FROM social_hypothesis_links ORDER BY updated_at DESC LIMIT ? OFFSET ?",(max(1,min(limit,100)),max(0,offset))).fetchall()]
    def refresh_profiles(self,min_cases=25,strong_threshold=.5):
        groups=self._db.execute("SELECT e.account_handle,r.asset_symbol,COUNT(*) cases,SUM(CASE WHEN r.reaction_strength>=? THEN 1 ELSE 0 END) strong,SUM(CASE WHEN r.reaction_direction='NONE' THEN 1 ELSE 0 END) none_count,SUM(CASE WHEN r.market_was_already_moving=1 THEN 1 ELSE 0 END) counter_count,GROUP_CONCAT(r.analysis_id) ids FROM social_reaction_results r JOIN social_events e ON e.event_id=r.social_event_id WHERE r.analysis_status='COMPLETED' GROUP BY e.account_handle,r.asset_symbol",(strong_threshold,)).fetchall();now=datetime.now(UTC).isoformat();created=0
        with self._lock,self._db:
            for row in groups:
                cases=int(row["cases"]);rate=int(row["strong"])/cases;association="HIGH" if cases>=min_cases and rate>=.5 else "MEDIUM" if cases>=min_cases and rate>=.25 else "LOW";confidence="HIGH" if cases>=min_cases*4 else "MEDIUM" if cases>=min_cases*2 else "LOW"
                pid=stable_id("social-profile",row["account_handle"],row["asset_symbol"]);self._db.execute("INSERT INTO social_account_profiles VALUES(?,?,?,?,?,?,?,?,?,?,1) ON CONFLICT(profile_id) DO UPDATE SET case_count=excluded.case_count,strong_reactions=excluded.strong_reactions,no_reactions=excluded.no_reactions,counter_reactions=excluded.counter_reactions,association_label=excluded.association_label,confidence_label=excluded.confidence_label,updated_at=excluded.updated_at",(pid,row["account_handle"],row["asset_symbol"],cases,row["strong"],row["none_count"],row["counter_count"],association,confidence,now))
                if cases>=min_cases:
                    sid=stable_id("social-suggestion",row["account_handle"],row["asset_symbol"]);statement=f"Posts von @{row['account_handle']} mit Bezug zu {row['asset_symbol']} stehen historisch möglicherweise mit kurzfristigen Marktreaktionen in zeitlichem Zusammenhang."
                    self._db.execute("INSERT INTO social_hypothesis_links VALUES(?,?,?,?,?,?,?,?,?,1) ON CONFLICT(suggestion_id) DO UPDATE SET case_count=excluded.case_count,source_analysis_ids=excluded.source_analysis_ids,updated_at=excluded.updated_at",(sid,row["account_handle"],row["asset_symbol"],statement,"NEW",cases,json.dumps(str(row["ids"]).split(",")),now,now));created+=1
        return created
    def latest_post_id(self,handle):
        row=self._db.execute("SELECT post_id FROM social_posts WHERE account_handle=? ORDER BY published_at DESC LIMIT 1",(handle,)).fetchone();return row[0] if row else None
    def update_worker_state(self,status,last_error=None,checked=0,ignored=0,interesting=0,high=0):
        now=datetime.now(UTC).isoformat();success=now if status=="OK" else None
        with self._lock,self._db:self._db.execute("INSERT INTO social_worker_state VALUES('x',?,?,?,?,?,?,?,?,?,?,1) ON CONFLICT(platform) DO UPDATE SET status=excluded.status,last_poll_at=excluded.last_poll_at,last_success_at=COALESCE(excluded.last_success_at,social_worker_state.last_success_at),last_error=excluded.last_error,posts_checked=social_worker_state.posts_checked+excluded.posts_checked,ignored=social_worker_state.ignored+excluded.ignored,interesting=social_worker_state.interesting+excluded.interesting,high_interest=social_worker_state.high_interest+excluded.high_interest,rate_limit_resets=social_worker_state.rate_limit_resets+excluded.rate_limit_resets,updated_at=excluded.updated_at",(status,now,success,last_error,checked,ignored,interesting,high,1 if status=="RATE_LIMITED" else 0,now))
    def worker_state(self):
        row=self._db.execute("SELECT * FROM social_worker_state WHERE platform='x'").fetchone();return _decode(row) if row else None
    def counts(self):
        def n(sql):return int(self._db.execute(sql).fetchone()[0])
        return {"posts":n("SELECT COUNT(*) FROM social_posts"),"ignored":n("SELECT COUNT(*) FROM social_posts WHERE relevance_status='IGNORED'"),"interesting":n("SELECT COUNT(*) FROM social_posts WHERE relevance_status='INTERESTING'"),"high_interest":n("SELECT COUNT(*) FROM social_posts WHERE relevance_status='HIGH_INTEREST'"),"tracking":n("SELECT COUNT(*) FROM social_events WHERE status IN ('NEW','TRACKING')"),"completed":n("SELECT COUNT(*) FROM social_events WHERE status='COMPLETED'"),"hypothesis_suggestions":n("SELECT COUNT(*) FROM social_hypothesis_links WHERE status IN ('NEW','READY_FOR_REVIEW')")}

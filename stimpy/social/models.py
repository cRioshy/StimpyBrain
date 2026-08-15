"""Immutable, validated social research records."""
from __future__ import annotations
import hashlib,math
from dataclasses import dataclass,field
from datetime import UTC,datetime
from enum import Enum

class RelevanceStatus(str,Enum): IGNORED="IGNORED";WATCH="WATCH";INTERESTING="INTERESTING";HIGH_INTEREST="HIGH_INTEREST";UNKNOWN="UNKNOWN"
class SentimentLabel(str,Enum): POSITIVE="POSITIVE";NEGATIVE="NEGATIVE";NEUTRAL="NEUTRAL";MIXED="MIXED";UNKNOWN="UNKNOWN"
class EventStatus(str,Enum): NEW="NEW";TRACKING="TRACKING";COMPLETED="COMPLETED";IGNORED="IGNORED";FAILED="FAILED"
class ReactionDirection(str,Enum): UP="UP";DOWN="DOWN";MIXED="MIXED";NONE="NONE";UNKNOWN="UNKNOWN"

def utc(value:datetime)->datetime:
    if value.tzinfo is None: raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(UTC)
def score(value:float)->float:
    value=float(value)
    if not math.isfinite(value) or not 0<=value<=1: raise ValueError("score must be finite and between 0 and 1")
    return value
def stable_id(prefix:str,*parts:object)->str:
    raw="\x1f".join(str(p) for p in parts).encode("utf-8");return f"{prefix}-{hashlib.sha256(raw).hexdigest()}"

@dataclass(frozen=True)
class SocialPostObservation:
    platform:str;account_id:str;account_handle:str;account_display_name:str;post_id:str;post_text:str;published_at:datetime
    collected_at:datetime=field(default_factory=lambda:datetime.now(UTC));language:str="und";topic_tags:tuple[str,...]=();asset_symbols:tuple[str,...]=()
    relevance_status:RelevanceStatus=RelevanceStatus.UNKNOWN;relevance_score:float=0;relevance_reasons:tuple[str,...]=()
    sentiment_label:SentimentLabel=SentimentLabel.UNKNOWN;sentiment_score:float=.5;intensity_score:float=0
    engagement_snapshot:dict=field(default_factory=dict);duplicate_group_id:str="";spam_probability:float=0;source_quality:float=1;schema_version:int=1
    social_post_id:str=field(init=False);post_text_hash:str=field(init=False)
    def __post_init__(self):
        text=" ".join(self.post_text.split())
        if not self.platform or not self.post_id or not self.account_handle or not text: raise ValueError("post identity and text required")
        if len(text)>4000: raise ValueError("post text exceeds hard limit")
        object.__setattr__(self,"post_text",text);object.__setattr__(self,"published_at",utc(self.published_at));object.__setattr__(self,"collected_at",utc(self.collected_at))
        for name in ("relevance_score","sentiment_score","intensity_score","spam_probability","source_quality"): object.__setattr__(self,name,score(getattr(self,name)))
        digest=hashlib.sha256(text.casefold().encode()).hexdigest();object.__setattr__(self,"post_text_hash",digest)
        object.__setattr__(self,"social_post_id",stable_id("social",self.platform.lower(),self.post_id))
        if not self.duplicate_group_id: object.__setattr__(self,"duplicate_group_id",stable_id("text",digest))

@dataclass(frozen=True)
class SocialInfluenceEvent:
    social_post_id:str;platform:str;account_handle:str;primary_topic:str;asset_symbols:tuple[str,...];published_at:datetime
    relevance_score:float;sentiment_label:SentimentLabel;intensity_score:float;market_snapshot_t0_id:str|None=None;status:EventStatus=EventStatus.NEW;schema_version:int=1
    event_id:str=field(init=False)
    def __post_init__(self):
        object.__setattr__(self,"published_at",utc(self.published_at));object.__setattr__(self,"relevance_score",score(self.relevance_score));object.__setattr__(self,"intensity_score",score(self.intensity_score));object.__setattr__(self,"event_id",stable_id("social-event",self.social_post_id))

@dataclass(frozen=True)
class SocialReactionAnalysis:
    social_event_id:str;asset_symbol:str;pre_event_return:float|None=None;post_5m_return:float|None=None;post_30m_return:float|None=None;post_2h_return:float|None=None;post_24h_return:float|None=None
    volume_change:float|None=None;volatility_change:float|None=None;reaction_strength:float=0;reaction_direction:ReactionDirection=ReactionDirection.UNKNOWN
    baseline_adjusted_reaction:float|None=None;market_was_already_moving:bool=False;confidence:float=0;analysis_status:str="PENDING";schema_version:int=1
    analysis_id:str=field(init=False)
    def __post_init__(self):
        object.__setattr__(self,"reaction_strength",score(self.reaction_strength));object.__setattr__(self,"confidence",score(self.confidence));object.__setattr__(self,"analysis_id",stable_id("social-analysis",self.social_event_id,self.asset_symbol))

"""Fail-closed Social Memory Lite configuration (RSS and Reddit only)."""
from __future__ import annotations
import os
from dataclasses import dataclass

def _bool(name,default=False):return os.getenv(name,"1" if default else "0").strip().lower() in {"1","true","yes","on"}
def _int(name,default,low,high):
    try:value=int(os.getenv(name,str(default)))
    except ValueError:value=default
    return max(low,min(value,high))

@dataclass(frozen=True)
class RssSource:
    source_id:str;display_name:str;url:str|None;status:str="AVAILABLE"

VERIFIED_RSS_SOURCES=(
    RssSource("coindesk","CoinDesk","https://www.coindesk.com/arc/outboundfeeds/rss/"),
    RssSource("cointelegraph","Cointelegraph","https://cointelegraph.com/rss"),
    RssSource("sec","SEC","https://www.sec.gov/news/pressreleases.rss"),
    RssSource("federal-reserve","Federal Reserve","https://www.federalreserve.gov/feeds/press_all.xml"),
    RssSource("binance","Binance",None,"UNAVAILABLE_NO_OFFICIAL_FEED"),
    RssSource("kraken","Kraken",None,"UNAVAILABLE_NO_OFFICIAL_FEED"),
)

@dataclass(frozen=True)
class SocialMemoryLiteConfig:
    enabled:bool=False;rss_enabled:bool=False;reddit_enabled:bool=False;poll_seconds:int=300
    assets:tuple[str,...]=("BTC","ETH","XRP");subreddits:tuple[str,...]=("Bitcoin","CryptoCurrency","Ethereum","XRP")
    reddit_client_id:str="";reddit_client_secret:str="";reddit_user_agent:str="StimpyBrain-SocialMemoryLite/1.0"
    rss_sources:tuple[RssSource,...]=VERIFIED_RSS_SOURCES;max_items_per_source:int=25;max_text_chars:int=1000;timeout_seconds:int=8;max_retries:int=2
    @classmethod
    def from_env(cls):
        assets=tuple(x.strip().upper() for x in os.getenv("STIMPY_SOCIAL_ASSETS","BTC,ETH,XRP").split(",") if x.strip().upper() in {"BTC","ETH","XRP"})
        subs=tuple(dict.fromkeys(x.strip().lstrip("r/") for x in os.getenv("STIMPY_REDDIT_SUBREDDITS","Bitcoin,CryptoCurrency,Ethereum,XRP").split(",") if x.strip()))
        return cls(_bool("STIMPY_SOCIAL_MEMORY_LITE_ENABLED"),_bool("STIMPY_RSS_ENABLED"),_bool("STIMPY_REDDIT_ENABLED"),
            _int("STIMPY_SOCIAL_POLL_SECONDS",300,60,86400),assets or ("BTC","ETH","XRP"),subs,
            os.getenv("REDDIT_CLIENT_ID",""),os.getenv("REDDIT_CLIENT_SECRET",""),os.getenv("REDDIT_USER_AGENT","StimpyBrain-SocialMemoryLite/1.0"),
            VERIFIED_RSS_SOURCES,_int("STIMPY_SOCIAL_MAX_ITEMS_PER_SOURCE",25,1,100),_int("STIMPY_SOCIAL_MAX_TEXT_CHARS",1000,128,4000),
            _int("STIMPY_SOCIAL_TIMEOUT_SECONDS",8,1,30),_int("STIMPY_SOCIAL_MAX_RETRIES",2,0,4))
    @property
    def status(self):
        if not self.enabled:return "DISABLED"
        if not self.rss_enabled and not self.reddit_enabled:return "DISABLED_NO_SOURCES"
        if self.reddit_enabled and not (self.reddit_client_id and self.reddit_client_secret):return "DEGRADED_REDDIT_NO_CREDENTIALS" if self.rss_enabled else "DISABLED_NO_CREDENTIALS"
        return "READY"

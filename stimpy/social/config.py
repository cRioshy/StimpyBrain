"""Fail-closed configuration for public social observation."""
from __future__ import annotations
import os
from dataclasses import dataclass

def _bool(name:str,default:bool=False)->bool:
    return os.getenv(name,"1" if default else "0").strip().lower() in {"1","true","yes","on"}
def _int(name:str,default:int,minimum:int,maximum:int)->int:
    try: value=int(os.getenv(name,str(default)))
    except ValueError: value=default
    return max(minimum,min(value,maximum))

@dataclass(frozen=True)
class SocialConfig:
    enabled:bool=False
    platform_x_enabled:bool=False
    accounts:tuple[str,...]=()
    bearer_token:str=""
    poll_seconds:int=120
    max_posts_per_account:int=25
    hypothesis_min_cases:int=25
    reaction_windows:tuple[str,...]=("5m","30m","2h","24h")
    max_text_chars:int=1000
    timeout_seconds:int=8
    max_retries:int=2
    @classmethod
    def from_env(cls):
        accounts=tuple(dict.fromkeys(x.strip().lstrip("@").lower() for x in os.getenv("STIMPY_SOCIAL_ACCOUNTS","").split(",") if x.strip()))
        allowed={"5m","30m","2h","24h"}
        windows=tuple(x.strip() for x in os.getenv("STIMPY_SOCIAL_REACTION_WINDOWS","5m,30m,2h,24h").split(",") if x.strip() in allowed)
        return cls(_bool("STIMPY_SOCIAL_ENABLED"),_bool("STIMPY_SOCIAL_PLATFORM_X_ENABLED"),accounts,
            os.getenv("X_BEARER_TOKEN",os.getenv("TWITTER_BEARER_TOKEN","")),
            _int("STIMPY_SOCIAL_POLL_SECONDS",120,30,86400),_int("STIMPY_SOCIAL_MAX_POSTS_PER_ACCOUNT",25,1,100),
            _int("STIMPY_SOCIAL_HYPOTHESIS_MIN_CASES",25,5,10000),windows or ("5m","30m","2h","24h"),
            _int("STIMPY_SOCIAL_MAX_TEXT_CHARS",1000,128,4000),_int("STIMPY_SOCIAL_TIMEOUT_SECONDS",8,1,30),_int("STIMPY_SOCIAL_MAX_RETRIES",2,0,4))
    @property
    def status(self)->str:
        if not self.enabled or not self.platform_x_enabled: return "DISABLED"
        if not self.bearer_token: return "DISABLED_NO_CREDENTIALS"
        if not self.accounts: return "DISABLED_NO_ACCOUNTS"
        return "READY"

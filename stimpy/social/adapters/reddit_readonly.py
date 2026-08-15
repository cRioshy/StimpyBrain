"""Official Reddit OAuth read-only adapter for public subreddit posts."""
from __future__ import annotations
import base64,json,time
from datetime import UTC,datetime,timedelta
from urllib.error import HTTPError,URLError
from urllib.parse import urlencode,quote
from urllib.request import Request,urlopen
from .base import PublicSocialPost

class RedditReadError(RuntimeError):pass
class RedditRateLimited(RedditReadError):pass
class RedditReadOnlyAdapter:
    def __init__(self,client_id,client_secret,user_agent,timeout_seconds=8,max_retries=2,opener=urlopen):
        if not client_id or not client_secret:raise ValueError("Reddit credentials required")
        self.client_id=client_id;self._secret=client_secret;self.user_agent=user_agent;self.timeout=timeout_seconds;self.retries=max_retries;self._open=opener;self._token="";self._expires=datetime.min.replace(tzinfo=UTC)
    def _access_token(self):
        if self._token and datetime.now(UTC)<self._expires:return self._token
        auth=base64.b64encode(f"{self.client_id}:{self._secret}".encode()).decode();request=Request("https://www.reddit.com/api/v1/access_token",data=urlencode({"grant_type":"client_credentials"}).encode(),headers={"Authorization":f"Basic {auth}","User-Agent":self.user_agent,"Content-Type":"application/x-www-form-urlencoded"},method="POST")
        try:
            with self._open(request,timeout=self.timeout) as response:payload=json.load(response)
            self._token=str(payload["access_token"]);self._expires=datetime.now(UTC)+timedelta(seconds=max(60,int(payload.get("expires_in",3600))-60));return self._token
        except Exception as exc:raise RedditReadError(f"OAuth failed: {type(exc).__name__}") from None
    def read_subreddit(self,subreddit,after=None,limit=25):
        params={"limit":max(1,min(limit,100)),"raw_json":1}
        if after:params["after"]=after
        url=f"https://oauth.reddit.com/r/{quote(subreddit,safe='')}/new?{urlencode(params)}"
        for attempt in range(self.retries+1):
            try:
                request=Request(url,headers={"Authorization":f"Bearer {self._access_token()}","User-Agent":self.user_agent,"Accept":"application/json"},method="GET")
                with self._open(request,timeout=self.timeout) as response:payload=json.load(response)
                children=payload.get("data",{}).get("children",[])
                if not isinstance(children,list):raise RedditReadError("invalid Reddit payload")
                result=[]
                for child in children:
                    item=child.get("data",{});post_id=str(item.get("name") or item.get("id") or "");title=str(item.get("title") or "");body=" — ".join(x for x in (title,str(item.get("selftext") or "")) if x)
                    if post_id and body:result.append(PublicSocialPost("reddit",str(item.get("subreddit_id") or subreddit),subreddit.lower(),f"r/{subreddit}",post_id,body,datetime.fromtimestamp(float(item["created_utc"]),UTC),"und",{"score":item.get("score",0),"num_comments":item.get("num_comments",0),"canonical_url":f"https://www.reddit.com{item.get('permalink','')}"}))
                return tuple(result)
            except HTTPError as exc:
                if exc.code==429:raise RedditRateLimited("Reddit rate limited") from None
                if exc.code==401:self._token=""
                if exc.code<500 or attempt>=self.retries:raise RedditReadError(f"Reddit HTTP {exc.code}") from None
            except (URLError,TimeoutError,json.JSONDecodeError) as exc:
                if attempt>=self.retries:raise RedditReadError(type(exc).__name__) from None
            time.sleep(min(2**attempt,4))
        return ()

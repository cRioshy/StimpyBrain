"""Official X API v2 GET-only adapter with bounded retries."""
from __future__ import annotations
import json,time
from datetime import datetime
from urllib.error import HTTPError,URLError
from urllib.parse import urlencode,quote
from urllib.request import Request,urlopen
from .base import PublicSocialPost

class SocialAdapterError(RuntimeError): pass
class SocialRateLimited(SocialAdapterError): pass
class XReadOnlyAdapter:
    base_url="https://api.x.com/2"
    def __init__(self,bearer_token:str,timeout_seconds:int=8,max_retries:int=2,opener=urlopen):
        if not bearer_token: raise ValueError("bearer token required")
        self._token=bearer_token;self.timeout=timeout_seconds;self.retries=max_retries;self._open=opener;self._users={}
    def _get(self,path:str,params:dict|None=None):
        url=f"{self.base_url}{path}"+(f"?{urlencode(params)}" if params else "")
        for attempt in range(self.retries+1):
            try:
                request=Request(url,headers={"Authorization":f"Bearer {self._token}","User-Agent":"StimpyBrain-SocialObserver/1"},method="GET")
                with self._open(request,timeout=self.timeout) as response: return json.loads(response.read().decode("utf-8"))
            except HTTPError as exc:
                if exc.code==429: raise SocialRateLimited("X API rate limited") from None
                if exc.code<500 or attempt>=self.retries: raise SocialAdapterError(f"X API HTTP {exc.code}") from None
            except (URLError,TimeoutError,json.JSONDecodeError) as exc:
                if attempt>=self.retries: raise SocialAdapterError(type(exc).__name__) from None
            time.sleep(min(2**attempt,4))
        raise SocialAdapterError("X API unavailable")
    def read_public_posts(self,handle:str,since_id:str|None=None,limit:int=25):
        handle=handle.lstrip("@");user=self._users.get(handle)
        if not user:
            payload=self._get(f"/users/by/username/{quote(handle,safe='')}",{"user.fields":"name,username"});user=payload.get("data")
            if not isinstance(user,dict) or not user.get("id"): raise SocialAdapterError("invalid X user payload")
            self._users[handle]=user
        params={"max_results":max(5,min(limit,100)),"tweet.fields":"created_at,lang,public_metrics","exclude":"retweets,replies"}
        if since_id: params["since_id"]=since_id
        payload=self._get(f"/users/{quote(str(user['id']),safe='')}/tweets",params);data=payload.get("data",[])
        if not isinstance(data,list): raise SocialAdapterError("invalid X timeline payload")
        result=[]
        for item in data:
            try: result.append(PublicSocialPost("x",str(user["id"]),str(user.get("username",handle)),str(user.get("name",handle)),str(item["id"]),str(item["text"]),datetime.fromisoformat(str(item["created_at"]).replace("Z","+00:00")),str(item.get("lang","und")),item.get("public_metrics",{})))
            except (KeyError,TypeError,ValueError): raise SocialAdapterError("invalid X post payload") from None
        return tuple(result)

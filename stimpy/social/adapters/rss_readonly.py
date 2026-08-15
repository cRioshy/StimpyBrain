"""Bounded RSS/Atom GET reader. It never follows article links."""
from __future__ import annotations
import hashlib,time
from datetime import UTC,datetime
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from urllib.error import HTTPError,URLError
from urllib.request import Request,urlopen
from xml.etree import ElementTree
from .base import PublicSocialPost

class FeedReadError(RuntimeError):pass
class _PlainText(HTMLParser):
    def __init__(self):super().__init__(convert_charrefs=True);self.parts=[]
    def handle_data(self,data):self.parts.append(data)
def _plain(value):
    parser=_PlainText();parser.feed(value or "");parser.close();return " ".join(" ".join(parser.parts).split())
def _text(node,names):
    for child in node.iter():
        if child.tag.rsplit("}",1)[-1] in names and child.text:return _plain(child.text)
    return ""
def _timestamp(value):
    if not value:return datetime.now(UTC)
    try:
        parsed=parsedate_to_datetime(value)
        return (parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)).astimezone(UTC)
    except (TypeError,ValueError,OverflowError):
        try:return datetime.fromisoformat(value.replace("Z","+00:00")).astimezone(UTC)
        except ValueError:return datetime.now(UTC)

class RssReadOnlyAdapter:
    def __init__(self,timeout_seconds=8,max_retries=2,max_bytes=1_000_000,opener=urlopen):self.timeout=timeout_seconds;self.retries=max_retries;self.max_bytes=max_bytes;self._open=opener;self._validators={}
    def read_source(self,source,limit=25):
        if not source.url:return ()
        headers={"User-Agent":"StimpyBrain-SocialMemoryLite/1.0","Accept":"application/rss+xml, application/atom+xml, application/xml, text/xml"};headers.update(self._validators.get(source.source_id,{}))
        for attempt in range(self.retries+1):
            try:
                request=Request(source.url,headers=headers,method="GET")
                with self._open(request,timeout=self.timeout) as response:
                    raw=response.read(self.max_bytes+1)
                    if len(raw)>self.max_bytes:raise FeedReadError("feed exceeds byte limit")
                    validators={}
                    if response.headers.get("ETag"):validators["If-None-Match"]=response.headers["ETag"]
                    if response.headers.get("Last-Modified"):validators["If-Modified-Since"]=response.headers["Last-Modified"]
                    self._validators[source.source_id]=validators
                root=ElementTree.fromstring(raw);items=[node for node in root.iter() if node.tag.rsplit("}",1)[-1] in {"item","entry"}][:max(1,min(limit,100))];result=[]
                for item in items:
                    title=_text(item,{"title"});summary=_text(item,{"description","summary","content"});link=_text(item,{"link"})
                    if not link:
                        for child in item.iter():
                            if child.tag.rsplit("}",1)[-1]=="link" and child.attrib.get("href"):link=child.attrib["href"];break
                    external=_text(item,{"guid","id"}) or link or hashlib.sha256(f"{title}|{summary}".encode()).hexdigest();published=_timestamp(_text(item,{"pubDate","published","updated"}));body=" — ".join(x for x in (title,summary) if x)
                    if body:result.append(PublicSocialPost("rss",source.source_id,source.source_id,source.display_name,external,body,published,"und",{"canonical_url":link}))
                return tuple(result)
            except HTTPError as exc:
                if exc.code==304:return ()
                if exc.code<500 or attempt>=self.retries:raise FeedReadError(f"RSS HTTP {exc.code}") from None
            except (URLError,TimeoutError,ElementTree.ParseError) as exc:
                if attempt>=self.retries:raise FeedReadError(type(exc).__name__) from None
            time.sleep(min(2**attempt,4))
        return ()

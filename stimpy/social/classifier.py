"""Transparent Phase-1 rule classifier; it never emits trade direction."""
from __future__ import annotations
import re
from dataclasses import dataclass
from .models import RelevanceStatus,SentimentLabel

ASSETS={
 "BTC":("btc","bitcoin"),"ETH":("eth","ethereum"),"XRP":("xrp","ripple"),"DOGE":("doge","dogecoin"),
 "CRYPTO_MARKET":("crypto","cryptocurrency","blockchain","wallet","exchange","hack","meme coin"),
 "REGULATION":("regulation","regulator","sec","ban","law","gesetz","regulierung"),"ETF":("etf",),
 "MINING":("mining","miner","hashrate","difficulty"),"MACRO":("fed","interest rate","zins","sanction","tariff","handelskrieg","central bank"),
 "STOCK_MARKET":("stock market","tesla","spacex","nasdaq")}
POSITIVE=("bullish","approval","approved","growth","strong","adoption","win","good","positiv","steigt")
NEGATIVE=("bearish","ban","hack","fraud","crash","weak","loss","bad","negativ","fällt")
INTENSE=("breaking","urgent","massive","historic","sofort","dringend","!!!")

@dataclass(frozen=True)
class Classification:
    topics:tuple[str,...];assets:tuple[str,...];status:RelevanceStatus;relevance_score:float;reasons:tuple[str,...];sentiment:SentimentLabel;sentiment_score:float;intensity_score:float

class SocialClassifier:
    version="social-v1"
    def classify(self,text:str)->Classification:
        normalized=" ".join(text.casefold().split());tokens=set(re.findall(r"[\w$-]+",normalized));found=[];reasons=[]
        for topic,terms in ASSETS.items():
            matches=[term for term in terms if (" " in term and term in normalized) or term in tokens]
            if matches: found.append(topic);reasons.append(f"{topic} matched: {', '.join(matches)}")
        direct=[x for x in found if x in {"BTC","ETH","XRP","DOGE"}]
        if direct and "CRYPTO_MARKET" not in found: found.append("CRYPTO_MARKET")
        rel=min(1,.18*len(found)+(.28 if direct else 0));status=RelevanceStatus.IGNORED
        if rel>=.75: status=RelevanceStatus.HIGH_INTEREST
        elif rel>=.48: status=RelevanceStatus.INTERESTING
        elif rel>=.18: status=RelevanceStatus.WATCH
        pos=sum(1 for x in POSITIVE if x in normalized);neg=sum(1 for x in NEGATIVE if x in normalized)
        sentiment=SentimentLabel.MIXED if pos and neg else SentimentLabel.POSITIVE if pos else SentimentLabel.NEGATIVE if neg else SentimentLabel.NEUTRAL
        sentiment_score=.5 if pos==neg else min(1,.5+.15*(pos-neg)) if pos>neg else max(0,.5-.15*(neg-pos))
        intensity=min(1,.2*sum(1 for x in INTENSE if x in normalized)+min(len(text)/500,.4))
        if not reasons: reasons=["No configured market relevance matched"]
        return Classification(tuple(found or ("UNKNOWN",)),tuple(direct or (["CRYPTO_MARKET"] if "CRYPTO_MARKET" in found else [])),status,round(rel,4),tuple(reasons),sentiment,round(sentiment_score,4),round(intensity,4))

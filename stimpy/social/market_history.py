"""Credential-free Coinbase public candle reader used only for reaction measurement."""
from __future__ import annotations
import json,math
from dataclasses import dataclass
from datetime import UTC,datetime,timedelta
from urllib.parse import urlencode
from urllib.request import Request,urlopen

@dataclass(frozen=True)
class MarketPoint:price:float;volume:float;volatility:float;timestamp:datetime;source:str="coinbase-exchange-public-candles"
class CoinbasePublicCandleFeed:
    def __init__(self,timeout_seconds=8,opener=urlopen):self.timeout=timeout_seconds;self._open=opener
    def read_at(self,asset,at):
        symbol=f"{asset.upper()}-USD";at=at.astimezone(UTC);start=at-timedelta(minutes=2);end=at+timedelta(minutes=2);params=urlencode({"granularity":60,"start":start.isoformat(),"end":end.isoformat()});request=Request(f"https://api.exchange.coinbase.com/products/{symbol}/candles?{params}",headers={"User-Agent":"StimpyBrain-SocialMemoryLite/1.0"},method="GET")
        with self._open(request,timeout=self.timeout) as response:rows=json.load(response)
        if not isinstance(rows,list) or not rows:raise RuntimeError("no public candle")
        row=min(rows,key=lambda x:abs(float(x[0])-at.timestamp()));low,high,opened,closed,volume=map(float,(row[1],row[2],row[3],row[4],row[5]));values=(low,high,opened,closed,volume)
        if not all(math.isfinite(x) for x in values) or opened<=0 or closed<=0:raise RuntimeError("invalid public candle")
        return MarketPoint(closed,volume,(high-low)/opened,datetime.fromtimestamp(float(row[0]),UTC))

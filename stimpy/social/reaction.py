"""Pure descriptive reaction calculations from frozen market snapshots."""
from __future__ import annotations
from .models import ReactionDirection,SocialReactionAnalysis

def _ret(start,end):return None if start in (None,0) or end is None else (end/start-1)*100
class ReactionAnalyzer:
    def analyze(self,event_id,asset,prices:dict[str,float],volumes:dict[str,float]|None=None):
        pre=_ret(prices.get("T-30m"),prices.get("T0"));returns={key:_ret(prices.get("T0"),prices.get(key)) for key in ("+5m","+30m","+2h","+24h")}
        available=[x for x in returns.values() if x is not None];latest=available[-1] if available else None;adjusted=None if latest is None else latest-(pre or 0)
        direction=ReactionDirection.UNKNOWN if latest is None else ReactionDirection.UP if latest>.1 else ReactionDirection.DOWN if latest<-.1 else ReactionDirection.NONE
        strength=min(1,abs(adjusted or 0)/5);already=abs(pre or 0)>.5;confidence=min(1,len(available)/4*(.7 if already else 1))
        volume_change=None
        if volumes: volume_change=_ret(volumes.get("T0"),volumes.get("+24h") or volumes.get("+2h") or volumes.get("+30m") or volumes.get("+5m"))
        return SocialReactionAnalysis(event_id,asset,pre,returns["+5m"],returns["+30m"],returns["+2h"],returns["+24h"],volume_change,None,strength,direction,adjusted,already,confidence,"COMPLETED" if len(available)==4 else "TRACKING")

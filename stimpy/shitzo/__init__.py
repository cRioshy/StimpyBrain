"""Disabled-by-default research foundation; never an order execution package."""

from .models import FeatureSnapshot, MarketTick, PaperPosition, TraderAccount, TraderDecision
from .lab import ShitzoLab
from .paper_broker import PaperBroker, PaperBrokerRules
from .price_window import PriceWindow
from .traders import ContrarianTrader, MomentumTrader, TrendTrader

__all__ = ["ContrarianTrader", "FeatureSnapshot", "MarketTick", "MomentumTrader", "PaperBroker", "PaperBrokerRules", "PaperPosition", "PriceWindow", "ShitzoLab", "TraderAccount", "TraderDecision", "TrendTrader"]

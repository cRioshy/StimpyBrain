"""Local orchestration for the isolated Stimpy reasoning prototype."""
from __future__ import annotations
from datetime import datetime
from typing import Protocol
from .evidence import EvidenceEngine
from .knowledge_graph import KnowledgeGraph
from .memory_service import Memory
from .models import IncubationRequest,PrototypeResult
from .observer import Observer
from .reasoning import ReasoningEngine
from .self_critic import SelfCritic

class IncubationPort(Protocol):
    def incubate(self,observation_id:str,question:str,reactivate_at:datetime)->IncubationRequest: ...

class StimpyPrototypeService:
    def __init__(self,store,observer=None,evidence=None,reasoning=None,critic=None,knowledge=None):
        self.observer=observer or Observer(); self.memory=Memory(store); self.evidence=evidence or EvidenceEngine()
        self.reasoning=reasoning or ReasoningEngine(); self.critic=critic or SelfCritic(); self.knowledge=knowledge or KnowledgeGraph(store)
    def process(self,decision):
        observation=self.observer.receive(decision); stored=self.memory.remember(observation)
        evidence=self.evidence.evaluate(observation); reasoning=self.reasoning.think(observation,evidence); critic=self.critic.analyse(observation)
        knowledge=self.knowledge.update(observation,reasoning,critic)
        return PrototypeResult(observation,stored,evidence,reasoning,critic,knowledge)

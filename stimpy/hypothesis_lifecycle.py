"""Explicit audited local lifecycle commands for hypotheses."""
from __future__ import annotations

import hashlib
import re
from datetime import UTC,datetime

from .models import HypothesisLifecycleAction,HypothesisLifecycleEvent,HypothesisStatus,parse_timestamp


_SECRET_ASSIGNMENT=re.compile(r"(?i)\b(token|password|authorization|cookie|secret|api[_-]?key)\s*[:=]")


class HypothesisLifecycleService:
    def __init__(self,store,max_reason_chars=2000,max_actor_chars=128,clock=None):
        self.store=store; self.max_reason_chars=max(64,min(int(max_reason_chars),10_000)); self.max_actor_chars=max(8,min(int(max_actor_chars),256)); self.clock=clock or (lambda:datetime.now(UTC))

    def reject(self,hypothesis_id,reason,actor="user"):
        return self._transition(hypothesis_id,HypothesisLifecycleAction.REJECT,HypothesisStatus.REJECTED,reason,actor)

    def archive(self,hypothesis_id,reason,actor="user"):
        return self._transition(hypothesis_id,HypothesisLifecycleAction.ARCHIVE,HypothesisStatus.ARCHIVED,reason,actor)

    def _transition(self,hypothesis_id,action,target,reason,actor):
        hypothesis=self.store.get_hypothesis(str(hypothesis_id))
        if hypothesis is None: raise KeyError("unknown hypothesis")
        reason=self._text(reason,"reason",self.max_reason_chars); actor=self._text(actor,"actor",self.max_actor_chars)
        latest=self.store.latest_hypothesis_lifecycle_event(hypothesis.hypothesis_id)
        if hypothesis.status is target:
            if latest and latest.action is action and latest.reason==reason and latest.actor==actor: return latest
            raise ValueError("hypothesis already has this terminal status with a different audit decision")
        if hypothesis.status is HypothesisStatus.ARCHIVED: raise ValueError("archived hypothesis cannot transition")
        event_id=hashlib.sha256(f"stimpy-hypothesis-lifecycle-v1|{hypothesis.hypothesis_id}|{action.value}|{hypothesis.status.value}|{target.value}|{reason}|{actor}".encode()).hexdigest()
        event=HypothesisLifecycleEvent(event_id,hypothesis.hypothesis_id,action,hypothesis.status,target,reason,actor,parse_timestamp(self.clock()))
        return self.store.apply_hypothesis_lifecycle_event(event)

    @staticmethod
    def _text(value,name,limit):
        if not isinstance(value,str): raise TypeError(f"{name} must be text")
        value=" ".join(value.split())
        if not value: raise ValueError(f"{name} must not be empty")
        if len(value)>limit: raise ValueError(f"{name} exceeds size limit")
        if _SECRET_ASSIGNMENT.search(value): raise ValueError(f"{name} appears to contain a secret")
        return value

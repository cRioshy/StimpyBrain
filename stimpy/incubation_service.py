"""Persistent, explicitly triggered incubation without a background scheduler."""
from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import UTC,datetime,timedelta

from .models import IncubationComparison,IncubationStatus,IncubationTask


def _aware(value:datetime)->datetime:
    if value.tzinfo is None: raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(UTC)


class IncubationService:
    def __init__(self,store,default_seconds=3600,max_retries=3,clock=None):
        self.store=store; self.default_seconds=max(1,int(default_seconds)); self.max_retries=max(1,int(max_retries)); self.clock=clock or (lambda:datetime.now(UTC))

    def create(self,observation_id:str,question:str,reactivate_at:datetime|None=None)->IncubationTask:
        question=str(question).strip()
        if not question or len(question)>1000: raise ValueError("question must contain 1 to 1000 characters")
        observation=self.store.get_observation(observation_id)
        reasoning=self.store.get_reasoning_for_observation(observation_id)
        if observation is None or reasoning is None: raise ValueError("stored observation and initial reasoning are required")
        now=_aware(self.clock()); due=_aware(reactivate_at) if reactivate_at else now+timedelta(seconds=self.default_seconds)
        if due<now: raise ValueError("reactivate_at must not be in the past")
        identity=f"incubation|v1|{reasoning.reasoning_id}|{question.casefold()}"
        task=IncubationTask(hashlib.sha256(identity.encode()).hexdigest(),observation["symbol"],question,observation_id,reasoning.reasoning_id,IncubationStatus.INCUBATING,now,due)
        return self.store.create_incubation(task)

    def mark_ready(self,now:datetime|None=None)->int:
        return self.store.mark_due_incubations_ready(_aware(now or self.clock()))

    def reactivate(self,incubation_id:str,new_observation_ids,final_reasoning_id:str,now:datetime|None=None)->IncubationTask:
        task=self._required(incubation_id)
        if task.status is IncubationStatus.RESOLVED: return task
        if task.status in {IncubationStatus.CANCELLED,IncubationStatus.FAILED}: raise ValueError(f"cannot reactivate {task.status.value.lower()} task")
        moment=_aware(now or self.clock())
        if moment<task.reactivate_at: raise ValueError("incubation is not ready")
        self.mark_ready(moment); task=self._required(incubation_id)
        if isinstance(new_observation_ids,(str,bytes)): raise TypeError("new_observation_ids must be a collection")
        new_ids=tuple(dict.fromkeys(str(item).strip() for item in new_observation_ids if str(item).strip()))
        if not new_ids or task.initial_observation_id in new_ids: raise ValueError("new independent observations are required")
        final=self.store.get_reasoning(final_reasoning_id)
        if final is None or final.observation_id not in new_ids: raise ValueError("final reasoning must belong to a new observation")
        if final.evidence_id==self.store.get_reasoning(task.initial_reasoning_id).evidence_id: raise ValueError("new evidence is required")
        for observation_id in new_ids:
            if self.store.get_observation(observation_id) is None or self.store.get_evidence_for_observation(observation_id) is None: raise ValueError("every new observation must have persisted evidence")
        initial=self.store.get_reasoning(task.initial_reasoning_id); initial_observation=self.store.get_observation(task.initial_observation_id); final_observation=self.store.get_observation(final.observation_id)
        comparison=IncubationComparison(initial.evidence_score,final.evidence_score,final.evidence_score-initial.evidence_score,initial.confidence,final.confidence,round(final.confidence-initial.confidence,12),str(initial_observation.get("decision") or "UNKNOWN"),str(final_observation.get("decision") or "UNKNOWN"),initial_observation.get("decision")!=final_observation.get("decision"),initial.conclusion,final.conclusion)
        changed=comparison.score_delta!=0 or comparison.confidence_delta!=0 or comparison.direction_changed
        conclusion="Reanalysis changed after new evidence." if changed else "Reanalysis remained unchanged after new evidence."
        resolved=replace(task,status=IncubationStatus.RESOLVED,reactivated_at=moment,final_reasoning_id=final.reasoning_id,new_observation_ids=new_ids,conclusion=conclusion,comparison=comparison,last_error=None)
        return self.store.update_incubation(resolved)

    def cancel(self,incubation_id:str)->IncubationTask:
        task=self._required(incubation_id)
        if task.status is IncubationStatus.CANCELLED: return task
        if task.status is IncubationStatus.RESOLVED: raise ValueError("resolved task cannot be cancelled")
        return self.store.update_incubation(replace(task,status=IncubationStatus.CANCELLED,last_error=None))

    def record_failure(self,incubation_id:str,error)->IncubationTask:
        task=self._required(incubation_id)
        if task.status in {IncubationStatus.RESOLVED,IncubationStatus.CANCELLED}: return task
        failures=task.failure_count+1; status=IncubationStatus.FAILED if failures>=self.max_retries else IncubationStatus.READY
        safe_error=type(error).__name__ if isinstance(error,BaseException) else "IncubationFailure"
        return self.store.update_incubation(replace(task,status=status,failure_count=failures,last_error=safe_error))

    def get(self,incubation_id:str)->IncubationTask|None: return self.store.get_incubation(incubation_id)
    def list(self,limit=100,offset=0,status=None): return self.store.list_incubations(limit,offset,status)
    def _required(self,incubation_id):
        task=self.get(incubation_id)
        if task is None: raise KeyError("unknown incubation task")
        return task

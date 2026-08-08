"""Explicit hypothesis reasoning, self-criticism and incubation."""
from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import UTC,datetime,timedelta

from .models import (CriticSeverity,HypothesisCritic,HypothesisIncubationComparison,HypothesisIncubationTask,
    HypothesisReasoning,HypothesisStatus,IncubationStatus,parse_timestamp)


class HypothesisAnalysisService:
    def __init__(self,store,hypothesis_engine,default_seconds=3600,max_retries=3,clock=None):
        self.store=store; self.engine=hypothesis_engine; self.default_seconds=max(1,int(default_seconds)); self.max_retries=max(1,int(max_retries)); self.clock=clock or (lambda:datetime.now(UTC))

    def analyse(self,hypothesis_id):
        hypothesis=self.store.get_hypothesis(hypothesis_id)
        if hypothesis is None: raise KeyError("unknown hypothesis")
        if hypothesis.status in {HypothesisStatus.REJECTED,HypothesisStatus.ARCHIVED}: raise ValueError("terminal hypothesis cannot be analysed")
        evaluation=self.store.latest_hypothesis_evaluation_model(hypothesis_id) or self.engine.evaluate_hypothesis(hypothesis_id)
        existing=self.store.get_hypothesis_reasoning_for_evaluation(evaluation.evaluation_id)
        if existing is not None: return existing,self.store.get_hypothesis_critic_for_reasoning(existing.reasoning_id)
        reasons=(f"{evaluation.supporting_count} independent cases support the hypothesis.",f"Weighted support is {evaluation.weighted_support:.3f}.")
        counter=(f"{evaluation.contradicting_count} independent cases contradict the hypothesis.",f"{evaluation.neutral_count} cases remain neutral or unresolved.")
        missing=tuple(f"coverage for required data: {item}" for item in hypothesis.required_data)+("independent audit of timeframe and market-regime coverage",)
        alternatives=("the association may reflect market regime rather than the proposed relation","the observations may share an unmeasured common driver")
        assumptions=("stored source identities represent independent origins","strength and quality labels are descriptive inputs, not calibrated probabilities")
        conclusion=f"Current evidence gives status {evaluation.status.value}; this is a non-causal research assessment, not a prediction or trading instruction."
        reasoning_id=hashlib.sha256(f"stimpy-hypothesis-reasoning-v1|{hypothesis_id}|{evaluation.evaluation_id}".encode()).hexdigest(); now=parse_timestamp(self.clock())
        reasoning=HypothesisReasoning(reasoning_id,hypothesis_id,evaluation.evaluation_id,reasons,counter,missing,alternatives,assumptions,conclusion,evaluation.confidence,evaluation.uncertainty,now)
        stored=self.store.save_hypothesis_reasoning(reasoning); return stored,self.criticise(stored)

    def criticise(self,reasoning):
        existing=self.store.get_hypothesis_critic_for_reasoning(reasoning.reasoning_id)
        if existing is not None: return existing
        evaluation=self.store.get_hypothesis_evaluation(reasoning.evaluation_id); hypothesis=self.store.get_hypothesis(reasoning.hypothesis_id)
        issues=[]; suggestions=[]; warnings=["look-ahead bias has not been independently audited","data leakage has not been independently audited"]
        if evaluation.independent_case_count<self.engine.min_supported_cases: issues.append("sample size is below the supported threshold"); suggestions.append("collect more independent cases")
        if evaluation.source_count<2: issues.append("source diversity is insufficient"); suggestions.append("add an independent source")
        if evaluation.contradicting_count==0: issues.append("no counterexample is currently stored"); suggestions.append("actively search for contradicting evidence")
        causal_terms=(" causes "," causes", "leads to","führt zu","verursacht")
        causal=any(term in f" {hypothesis.statement.casefold()} " for term in causal_terms)
        if causal: issues.append("statement may imply causality from observational evidence"); warnings.append("correlation must not be presented as causation")
        calibration=evaluation.confidence>.70 or (evaluation.independent_case_count<self.engine.min_provisional_cases and evaluation.confidence>.49)
        if calibration: issues.append("confidence may be too high for the available evidence"); suggestions.append("retain a stricter confidence cap")
        severity=CriticSeverity.HIGH if causal else CriticSeverity.MEDIUM if len(issues)>=2 else CriticSeverity.LOW if issues else CriticSeverity.INFO
        critic_id=hashlib.sha256(f"stimpy-hypothesis-critic-v1|{reasoning.reasoning_id}".encode()).hexdigest(); now=parse_timestamp(self.clock())
        return self.store.save_hypothesis_critic(HypothesisCritic(critic_id,reasoning.hypothesis_id,reasoning.reasoning_id,tuple(issues),tuple(suggestions),severity,tuple(warnings),calibration,now))

    def create_incubation(self,hypothesis_id,question,seconds=None):
        question=" ".join(str(question).split())
        if not question or len(question)>2000: raise ValueError("bounded incubation question is required")
        reasoning,critic=self.analyse(hypothesis_id); evaluation=self.store.get_hypothesis_evaluation(reasoning.evaluation_id); evidence=self.store.load_hypothesis_evidence(hypothesis_id)
        if not evidence: raise ValueError("hypothesis incubation requires persisted evidence")
        incubation_id=hashlib.sha256(f"stimpy-hypothesis-incubation-v1|{hypothesis_id}|{evaluation.evaluation_id}|{question.casefold()}".encode()).hexdigest()
        existing=self.store.get_hypothesis_incubation(incubation_id)
        if existing is not None: return existing
        now=parse_timestamp(self.clock()); delay=self.default_seconds if seconds is None else max(1,int(seconds))
        task=HypothesisIncubationTask(incubation_id,hypothesis_id,question,evaluation.evaluation_id,reasoning.reasoning_id,tuple(sorted(item.evidence_id for item in evidence)),IncubationStatus.INCUBATING,now,now+timedelta(seconds=delay))
        stored=self.store.create_hypothesis_incubation(task); self.store.set_hypothesis_status(hypothesis_id,HypothesisStatus.INCUBATING,now); return stored

    def mark_ready(self,now=None): return self.store.mark_due_hypothesis_incubations_ready(parse_timestamp(now or self.clock()))

    def reactivate(self,incubation_id,now=None):
        task=self.store.get_hypothesis_incubation(incubation_id)
        if task is None: raise KeyError("unknown hypothesis incubation")
        if task.status is IncubationStatus.RESOLVED: return task
        hypothesis=self.store.get_hypothesis(task.hypothesis_id)
        if hypothesis.status in {HypothesisStatus.REJECTED,HypothesisStatus.ARCHIVED}: raise ValueError("terminal hypothesis cannot be reactivated")
        now=parse_timestamp(now or self.clock())
        if task.status is IncubationStatus.INCUBATING and now>=task.reactivate_at: self.mark_ready(now); task=self.store.get_hypothesis_incubation(incubation_id)
        if task.status is not IncubationStatus.READY: raise ValueError("hypothesis incubation is not ready")
        current=self.store.load_hypothesis_evidence(task.hypothesis_id); initial=set(task.initial_evidence_ids); new=tuple(sorted(item.evidence_id for item in current if item.evidence_id not in initial))
        if not new: raise ValueError("new independent hypothesis evidence is required")
        final_evaluation=self.engine.evaluate_hypothesis(task.hypothesis_id); final_reasoning,final_critic=self.analyse(task.hypothesis_id); initial_evaluation=self.store.get_hypothesis_evaluation(task.initial_evaluation_id)
        comparison=HypothesisIncubationComparison(initial_evaluation.status.value,final_evaluation.status.value,initial_evaluation.status!=final_evaluation.status,final_evaluation.evidence_ratio-initial_evaluation.evidence_ratio,final_evaluation.confidence-initial_evaluation.confidence,final_evaluation.independent_case_count-initial_evaluation.independent_case_count,final_evaluation.contradicting_count-initial_evaluation.contradicting_count)
        conclusion="Hypothesis assessment changed after new independent evidence." if comparison.status_changed or comparison.evidence_ratio_delta else "Hypothesis status remained stable after new independent evidence."
        resolved=replace(task,status=IncubationStatus.RESOLVED,reactivated_at=now,final_evaluation_id=final_evaluation.evaluation_id,final_reasoning_id=final_reasoning.reasoning_id,new_evidence_ids=new,comparison=comparison,conclusion=conclusion,last_error=None)
        return self.store.update_hypothesis_incubation(resolved)

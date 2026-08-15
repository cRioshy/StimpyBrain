"""Hypothesis-only checks for possible miscalibration and inconsistent outcomes."""
import hashlib
from .models import CriticResult,CriticSeverity,Observation,ReasoningResult,utc_now

class SelfCritic:
    def analyse(self,observation:Observation,reasoning:ReasoningResult|None=None)->CriticResult:
        issues=[]; suggestions=[]; level=0
        if observation.confidence>.9:
            issues.append("Reported confidence may be unusually high."); suggestions.append("Review confidence calibration against a larger sample."); level=max(level,1)
        if observation.outcome=="LOSS" and observation.confidence>.8:
            issues.append("Confidence could be over-calibrated for this losing case."); suggestions.append("Compare similar cases before changing calibration."); level=max(level,2)
        if observation.profit<-5:
            issues.append("The negative result may indicate that the risk boundary needs review."); suggestions.append("Review the simulated risk boundary; this is not a stop-loss verdict."); level=max(level,2)
        if (observation.outcome=="WIN" and observation.profit<0) or (observation.outcome=="LOSS" and observation.profit>0):
            issues.append("Reported profit and outcome appear inconsistent."); suggestions.append("Verify source-data semantics and sign conventions."); level=max(level,3)
        if observation.outcome in {"UNKNOWN","OPEN"}:
            issues.append("Outcome is not final, so the assessment remains uncertain."); suggestions.append("Re-evaluate only after a validated final outcome is available."); level=max(level,1)
        severity=(CriticSeverity.INFO,CriticSeverity.LOW,CriticSeverity.MEDIUM,CriticSeverity.HIGH)[level]
        reasoning_id=reasoning.reasoning_id if reasoning else hashlib.sha256(f"reasoning|unlinked|{observation.observation_id}".encode()).hexdigest()
        critic_id=hashlib.sha256(f"critic|v1|{observation.observation_id}|{reasoning_id}".encode()).hexdigest()
        calibration_warning=observation.confidence>.9 or (observation.outcome=="LOSS" and observation.confidence>.8)
        return CriticResult(observation.observation_id,tuple(issues),severity.value,tuple(dict.fromkeys(suggestions)),utc_now(),critic_id,reasoning_id,calibration_warning,1)

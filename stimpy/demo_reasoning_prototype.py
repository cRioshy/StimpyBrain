"""Clearly simulated local demo for the reasoning prototype."""
from __future__ import annotations
import tempfile
from pathlib import Path
from .observation_store import ObservationStore
from .prototype import StimpyPrototypeService

SIMULATED_PAYLOAD={"symbol":"BTCUSDT","market":"crypto","decision":"LONG","confidence":.87,"outcome":"WIN","profit":7.2,"source":"demo"}

def run_demo(data_dir=None,output=print):
    owned=None
    if data_dir is None:
        owned=tempfile.TemporaryDirectory(prefix="stimpy-demo-"); data_dir=Path(owned.name)
    root=Path(data_dir); store=ObservationStore(root/"database"/"stimpy_demo.sqlite3",root)
    try: result=StimpyPrototypeService(store).process(SIMULATED_PAYLOAD)
    finally: store.close()
    output("SIMULATED LOCAL DEMO - NO MARKET CONNECTION")
    output("Stimpy Observation\n-------------------")
    output(f"Symbol: {result.observation.symbol}\nDecision: {result.observation.decision}\nConfidence: {result.observation.confidence}\nOutcome: {result.observation.outcome}\nProfit: {result.observation.profit}")
    output("\nEvidence\n-------------------")
    output(f"Score: {result.evidence.score}\nSupporting: {list(result.evidence.supporting_evidence)}\nContradicting: {list(result.evidence.contradicting_evidence)}")
    output("\nReasoning\n-------------------")
    output(f"Reasons: {list(result.reasoning.reasons)}\nCounterarguments: {list(result.reasoning.counterarguments)}\nConclusion: {result.reasoning.conclusion}\nUncertainty: {result.reasoning.uncertainty}")
    output("\nSelf Critic\n-------------------")
    output(f"Issues: {list(result.critic.issues)}\nSeverity: {result.critic.severity}\nSuggestions: {list(result.critic.suggestions)}")
    if owned: owned.cleanup()
    return result

if __name__=="__main__": run_demo()

"""Central topology and phase-mode enforcement."""

from __future__ import annotations

from .models import WorkflowDefinition


REQUIRED_TOPOLOGY = (
    "DataQuality",
    "Features",
    "Prediction",
    "MomentumGate",
    "RiskGate",
    "DecisionGate",
)
OPTIONAL_FINAL_NODE = "PaperSimulation"


class WorkflowValidator:
    """Reject every definition that could bypass or duplicate a safety gate."""

    @staticmethod
    def validate(workflow: WorkflowDefinition) -> None:
        if not workflow.workflow_id.strip() or not workflow.name.strip():
            raise ValueError("workflow_id and name must not be empty")
        if workflow.version < 1 or workflow.schema_version != 1:
            raise ValueError("unsupported workflow or schema version")
        if workflow.mode != "observe":
            raise ValueError("StimpyBrain phase 1 permits observe mode only")
        if len(set(workflow.nodes)) != len(workflow.nodes):
            raise ValueError("workflow nodes must not be duplicated")
        allowed = (REQUIRED_TOPOLOGY, REQUIRED_TOPOLOGY + (OPTIONAL_FINAL_NODE,))
        if workflow.nodes not in allowed:
            raise ValueError(
                "workflow topology must contain every safety node exactly once and in order"
            )

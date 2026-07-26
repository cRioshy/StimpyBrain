"""Deterministic observe-only phase-1 workflow nodes."""
from __future__ import annotations

from datetime import UTC, datetime
from math import isfinite
from typing import Any

from ..contracts import WorkflowNode
from ..models import NodeResult, NodeStatus


def _number(data: dict[str, Any], key: str, *, positive: bool = True, maximum: float = 1e15) -> float:
    value = float(data[key])
    if not isfinite(value) or (positive and value <= 0) or value > maximum:
        raise ValueError(f"invalid {key}")
    return value


class BaseNode(WorkflowNode):
    version = 1
    timeout_seconds = 2.0
    retry_limit = 0
    retry_delay_seconds = 0.0

    def validate_input(self, input_data: dict[str, Any]) -> None:
        if not isinstance(input_data, dict):
            raise TypeError("node input must be a dictionary")


class DataQualityNode(BaseNode):
    node_type = "DataQuality"

    async def execute(self, context, input_data):
        price = _number(input_data, "price")
        previous = _number(input_data, "previous_price")
        volume = _number(input_data, "volume", positive=False)
        if volume < 0:
            raise ValueError("invalid volume")
        stamp = datetime.fromisoformat(str(input_data["timestamp"]).replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        age = (datetime.now(UTC) - stamp.astimezone(UTC)).total_seconds()
        if age < -5 or age > 300:
            return NodeResult(NodeStatus.REJECTED, reason="timestamp outside allowed window")
        return NodeResult(NodeStatus.COMPLETED, {"price": price, "previous_price": previous, "volume": volume})


class FeaturesNode(BaseNode):
    node_type = "Features"
    async def execute(self, context, data):
        return NodeResult(NodeStatus.COMPLETED, {"momentum": (data["price"] - data["previous_price"]) / data["previous_price"]})


class PredictionNode(BaseNode):
    node_type = "Prediction"
    async def execute(self, context, data):
        momentum = float(data["momentum"])
        return NodeResult(NodeStatus.COMPLETED, {"prediction": "UP" if momentum > 0 else "DOWN", "confidence": min(abs(momentum) * 10, 1.0)})


class MomentumGateNode(BaseNode):
    node_type = "MomentumGate"
    async def execute(self, context, data):
        if abs(float(data["momentum"])) < 0.0001:
            return NodeResult(NodeStatus.REJECTED, reason="insufficient momentum")
        return NodeResult(NodeStatus.COMPLETED, {"momentum_gate": "passed"})


class RiskGateNode(BaseNode):
    node_type = "RiskGate"
    async def execute(self, context, data):
        confidence = float(data["confidence"])
        if not isfinite(confidence) or confidence < 0 or confidence > 1:
            return NodeResult(NodeStatus.REJECTED, reason="invalid confidence")
        return NodeResult(NodeStatus.COMPLETED, {"risk_gate": "passed"})


class DecisionGateNode(BaseNode):
    node_type = "DecisionGate"
    async def execute(self, context, data):
        return NodeResult(NodeStatus.COMPLETED, {"decision": "OBSERVE_" + str(data["prediction"]), "orders_created": 0})


class PaperSimulationNode(BaseNode):
    node_type = "PaperSimulation"
    async def execute(self, context, data):
        return NodeResult(NodeStatus.COMPLETED, {"paper_simulation": "disabled", "orders_created": 0})

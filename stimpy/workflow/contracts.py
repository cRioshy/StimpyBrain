"""Stable allow-listed contract implemented by every workflow node."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .models import ExecutionContext, NodeResult


class WorkflowNode(ABC):
    node_type: str
    version: int = 1
    timeout_seconds: float = 5.0
    retry_limit: int = 0
    retry_delay_seconds: float = 0.05

    @abstractmethod
    async def execute(
        self,
        context: ExecutionContext,
        input_data: dict[str, Any],
    ) -> NodeResult:
        """Process validated input without invoking another node."""

    def validate_input(self, input_data: dict[str, Any]) -> None:
        if not isinstance(input_data, dict):
            raise TypeError("node input must be a dictionary")


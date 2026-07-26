"""Allow-listed registry; workflow data can never select arbitrary code."""

from __future__ import annotations

from .contracts import WorkflowNode


class NodeRegistry:
    def __init__(self) -> None:
        self._nodes: dict[str, WorkflowNode] = {}

    def register(self, node: WorkflowNode) -> None:
        if not node.node_type:
            raise ValueError("node_type must not be empty")
        if node.node_type in self._nodes:
            raise ValueError(f"node already registered: {node.node_type}")
        self._nodes[node.node_type] = node

    def get(self, node_type: str) -> WorkflowNode:
        try:
            return self._nodes[node_type]
        except KeyError as exc:
            raise KeyError(f"workflow references unknown node: {node_type}") from exc


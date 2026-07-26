"""Terminal-only execution models for the Stimpy workflow gate."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4


def utc_now() -> datetime:
    return datetime.now(UTC)


class NodeStatus(StrEnum):
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"


class ExecutionStatus(StrEnum):
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class WorkflowDefinition:
    workflow_id: str
    name: str
    version: int
    nodes: tuple[str, ...]
    mode: str = "observe"
    schema_version: int = 1


@dataclass(frozen=True)
class ExecutionContext:
    workflow: WorkflowDefinition
    event_id: str
    correlation_id: str
    market: str
    symbol: str
    execution_id: str = field(default_factory=lambda: str(uuid4()))
    started_at: datetime = field(default_factory=utc_now)


@dataclass
class NodeResult:
    status: NodeStatus
    output_data: dict[str, Any] = field(default_factory=dict)
    reason: str | None = None
    started_at: datetime = field(default_factory=utc_now)
    finished_at: datetime = field(default_factory=utc_now)
    retry_count: int = 0
    error_message: str | None = None

    @classmethod
    def completed(cls, output_data: dict[str, Any]) -> "NodeResult":
        return cls(NodeStatus.COMPLETED, output_data=output_data)

    @classmethod
    def rejected(cls, reason: str, output_data: dict[str, Any] | None = None) -> "NodeResult":
        return cls(NodeStatus.REJECTED, output_data=output_data or {}, reason=reason)


@dataclass(frozen=True)
class NodeAudit:
    node_type: str
    node_version: int
    input_data: dict[str, Any]
    result: NodeResult


@dataclass(frozen=True)
class WorkflowRunResult:
    execution_id: str
    status: ExecutionStatus
    final_data: dict[str, Any]
    reason: str | None = None
    duplicate: bool = False

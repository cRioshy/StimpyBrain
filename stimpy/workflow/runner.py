"""Sequential, terminal-only workflow runner with central safety enforcement."""

from __future__ import annotations

import asyncio
from typing import Any

from .models import (
    ExecutionContext,
    ExecutionStatus,
    NodeAudit,
    NodeResult,
    NodeStatus,
    WorkflowDefinition,
    WorkflowRunResult,
    utc_now,
)
from .registry import NodeRegistry
from .repository import DuplicateExecutionError, SQLiteWorkflowRepository
from .validator import WorkflowValidator


class WorkflowRunner:
    def __init__(self, registry: NodeRegistry, repository: SQLiteWorkflowRepository) -> None:
        self._registry = registry
        self._repository = repository

    async def run(
        self,
        workflow: WorkflowDefinition,
        input_data: dict[str, Any],
        *,
        event_id: str,
        correlation_id: str,
        market: str,
        symbol: str,
    ) -> WorkflowRunResult:
        WorkflowValidator.validate(workflow)
        if not event_id.strip() or not correlation_id.strip():
            raise ValueError("event_id and correlation_id must not be empty")
        existing = self._repository.find_duplicate(event_id, correlation_id)
        if existing is not None:
            return self._duplicate_result(existing)
        if not self._repository.claim(event_id, correlation_id):
            return WorkflowRunResult(
                execution_id="",
                status=ExecutionStatus.REJECTED,
                final_data={},
                reason="duplicate execution is already running",
                duplicate=True,
            )

        context = ExecutionContext(
            workflow=workflow,
            event_id=event_id,
            correlation_id=correlation_id,
            market=market,
            symbol=symbol,
        )
        current_data = dict(input_data)
        audits: list[NodeAudit] = []
        result: WorkflowRunResult | None = None
        try:
            for node_type in workflow.nodes:
                node = self._registry.get(node_type)
                node_input = dict(current_data)
                node_result = await self._execute_node(node, context, node_input)
                audits.append(NodeAudit(node.node_type, node.version, node_input, node_result))

                if node_result.status is NodeStatus.REJECTED:
                    result = WorkflowRunResult(
                        context.execution_id,
                        ExecutionStatus.REJECTED,
                        node_result.output_data,
                        node_result.reason,
                    )
                    break
                if node_result.status is NodeStatus.TIMEOUT:
                    result = WorkflowRunResult(
                        context.execution_id,
                        ExecutionStatus.TIMEOUT,
                        node_result.output_data,
                        node_result.error_message,
                    )
                    break
                if node_result.status is NodeStatus.CANCELLED:
                    result = WorkflowRunResult(
                        context.execution_id,
                        ExecutionStatus.CANCELLED,
                        node_result.output_data,
                        node_result.error_message or "workflow cancelled",
                    )
                    break
                if node_result.status is NodeStatus.FAILED:
                    result = WorkflowRunResult(
                        context.execution_id,
                        ExecutionStatus.FAILED,
                        node_result.output_data,
                        node_result.error_message,
                    )
                    break
                current_data.update(node_result.output_data)
            if result is None:
                result = WorkflowRunResult(
                    context.execution_id,
                    ExecutionStatus.COMPLETED,
                    current_data,
                )
        except asyncio.CancelledError:
            result = WorkflowRunResult(
                context.execution_id,
                ExecutionStatus.CANCELLED,
                current_data,
                "workflow task cancelled",
            )
        except Exception as exc:
            result = WorkflowRunResult(
                context.execution_id,
                ExecutionStatus.FAILED,
                current_data,
                str(exc),
            )
        finally:
            if result is None:
                result = WorkflowRunResult(
                    context.execution_id,
                    ExecutionStatus.FAILED,
                    current_data,
                    "workflow ended without terminal result",
                )
            try:
                self._repository.save_terminal_execution(context, result, audits)
            except DuplicateExecutionError:
                existing = self._repository.find_duplicate(event_id, correlation_id)
                if existing is not None:
                    result = self._duplicate_result(existing)
                else:
                    raise
            finally:
                self._repository.release_claim(event_id, correlation_id)
        return result

    async def _execute_node(self, node, context, input_data) -> NodeResult:
        node.validate_input(input_data)
        started_at = utc_now()
        for attempt in range(node.retry_limit + 1):
            try:
                result = await asyncio.wait_for(
                    node.execute(context, input_data),
                    timeout=node.timeout_seconds,
                )
                if result.status not in set(NodeStatus):
                    raise ValueError("node returned unsupported status")
                result.started_at = started_at
                result.finished_at = utc_now()
                result.retry_count = attempt
                return result
            except asyncio.CancelledError:
                return NodeResult(
                    NodeStatus.CANCELLED,
                    started_at=started_at,
                    finished_at=utc_now(),
                    retry_count=attempt,
                    error_message=f"{node.node_type} cancelled",
                )
            except asyncio.TimeoutError:
                if attempt >= node.retry_limit:
                    return NodeResult(
                        NodeStatus.TIMEOUT,
                        started_at=started_at,
                        finished_at=utc_now(),
                        retry_count=attempt,
                        error_message=f"{node.node_type} exceeded {node.timeout_seconds}s",
                    )
            except Exception as exc:
                if attempt >= node.retry_limit:
                    return NodeResult(
                        NodeStatus.FAILED,
                        started_at=started_at,
                        finished_at=utc_now(),
                        retry_count=attempt,
                        error_message=str(exc),
                    )
            await asyncio.sleep(node.retry_delay_seconds)
        raise RuntimeError("unreachable retry state")

    @staticmethod
    def _duplicate_result(existing: dict[str, Any]) -> WorkflowRunResult:
        return WorkflowRunResult(
            execution_id=str(existing["id"]),
            status=ExecutionStatus(str(existing["status"])),
            final_data={"decision": existing.get("final_decision")},
            reason="duplicate event_id or correlation_id",
            duplicate=True,
        )


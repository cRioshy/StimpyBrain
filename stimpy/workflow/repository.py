"""Versioned, synchronized SQLite audit repository."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from threading import RLock
from typing import Any

from .contracts import WorkflowNode
from .models import ExecutionContext, ExecutionStatus, NodeAudit, WorkflowRunResult, utc_now
from .sanitizer import AuditSanitizer


MIGRATION_1 = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS workflow_executions (
    id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL UNIQUE,
    correlation_id TEXT NOT NULL UNIQUE,
    workflow_id TEXT NOT NULL,
    workflow_name TEXT NOT NULL,
    workflow_version INTEGER NOT NULL,
    schema_version INTEGER NOT NULL,
    market TEXT NOT NULL,
    symbol TEXT NOT NULL,
    mode TEXT NOT NULL CHECK(mode = 'observe'),
    status TEXT NOT NULL CHECK(status IN ('COMPLETED','REJECTED','FAILED','TIMEOUT','CANCELLED')),
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL,
    final_decision TEXT,
    reason TEXT
);
CREATE TABLE IF NOT EXISTS node_executions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_execution_id TEXT NOT NULL,
    node_type TEXT NOT NULL,
    node_version INTEGER NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('COMPLETED','REJECTED','FAILED','TIMEOUT','CANCELLED')),
    input_data TEXT NOT NULL,
    output_data TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL,
    duration_ms REAL NOT NULL,
    retry_count INTEGER NOT NULL,
    reason TEXT,
    error_message TEXT,
    FOREIGN KEY(workflow_execution_id) REFERENCES workflow_executions(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_workflow_definition ON workflow_executions(workflow_id, id);
CREATE INDEX IF NOT EXISTS idx_node_execution_workflow ON node_executions(workflow_execution_id, id);
"""


class DuplicateExecutionError(RuntimeError):
    pass


class SQLiteWorkflowRepository:
    def __init__(self, database_path: str | Path, sanitizer: AuditSanitizer | None = None) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._claims: set[str] = set()
        self._sanitizer = sanitizer or AuditSanitizer()
        try:
            self._connection = sqlite3.connect(self.database_path, check_same_thread=False)
            self._connection.row_factory = sqlite3.Row
            self._connection.execute("PRAGMA foreign_keys = ON")
            check = self._connection.execute("PRAGMA quick_check").fetchone()[0]
            if check != "ok":
                raise sqlite3.DatabaseError(f"SQLite quick_check failed: {check}")
            self._migrate()
        except sqlite3.DatabaseError:
            if hasattr(self, "_connection"):
                self._connection.close()
            raise

    def _migrate(self) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
            )
            applied = {
                row[0] for row in self._connection.execute("SELECT version FROM schema_migrations")
            }
            if 1 not in applied:
                self._connection.executescript(MIGRATION_1)
                self._connection.execute(
                    "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                    (1, utc_now().isoformat()),
                )

    @property
    def foreign_keys_enabled(self) -> bool:
        with self._lock:
            return bool(self._connection.execute("PRAGMA foreign_keys").fetchone()[0])

    @property
    def schema_version(self) -> int:
        with self._lock:
            row = self._connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()
            return int(row[0] or 0)

    def find_duplicate(self, event_id: str, correlation_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM workflow_executions WHERE event_id = ? OR correlation_id = ? LIMIT 1",
                (event_id, correlation_id),
            ).fetchone()
            return dict(row) if row else None

    def claim(self, event_id: str, correlation_id: str) -> bool:
        """Reserve both idempotency keys without creating a durable RUNNING row."""

        keys = {f"event:{event_id}", f"correlation:{correlation_id}"}
        with self._lock:
            if keys & self._claims or self.find_duplicate(event_id, correlation_id):
                return False
            self._claims.update(keys)
            return True

    def release_claim(self, event_id: str, correlation_id: str) -> None:
        with self._lock:
            self._claims.discard(f"event:{event_id}")
            self._claims.discard(f"correlation:{correlation_id}")

    def save_terminal_execution(
        self,
        context: ExecutionContext,
        result: WorkflowRunResult,
        audits: list[NodeAudit],
    ) -> None:
        """Persist the complete run atomically; no durable RUNNING state exists."""

        finished_at = utc_now()
        with self._lock:
            try:
                with self._connection:
                    self._connection.execute(
                        """INSERT INTO workflow_executions
                        (id,event_id,correlation_id,workflow_id,workflow_name,workflow_version,
                         schema_version,market,symbol,mode,status,started_at,finished_at,
                         final_decision,reason)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (
                            context.execution_id,
                            context.event_id,
                            context.correlation_id,
                            context.workflow.workflow_id,
                            context.workflow.name,
                            context.workflow.version,
                            context.workflow.schema_version,
                            context.market,
                            context.symbol,
                            context.workflow.mode,
                            result.status.value,
                            context.started_at.isoformat(),
                            finished_at.isoformat(),
                            result.final_data.get("decision"),
                            result.reason,
                        ),
                    )
                    for audit in audits:
                        node = audit.result
                        duration_ms = max(
                            (node.finished_at - node.started_at).total_seconds() * 1000,
                            0.0,
                        )
                        self._connection.execute(
                            """INSERT INTO node_executions
                            (workflow_execution_id,node_type,node_version,status,input_data,
                             output_data,started_at,finished_at,duration_ms,retry_count,reason,error_message)
                            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (
                                context.execution_id,
                                audit.node_type,
                                audit.node_version,
                                node.status.value,
                                self._sanitizer.dumps(audit.input_data),
                                self._sanitizer.dumps(node.output_data),
                                node.started_at.isoformat(),
                                node.finished_at.isoformat(),
                                duration_ms,
                                node.retry_count,
                                node.reason,
                                node.error_message,
                            ),
                        )
            except sqlite3.IntegrityError as exc:
                if "UNIQUE constraint failed" in str(exc):
                    raise DuplicateExecutionError(str(exc)) from exc
                raise

    def get_execution(self, execution_id: str) -> dict[str, Any] | None:
        with self._lock:
            execution = self._connection.execute(
                "SELECT * FROM workflow_executions WHERE id = ?", (execution_id,)
            ).fetchone()
            if execution is None:
                return None
            nodes = self._connection.execute(
                "SELECT * FROM node_executions WHERE workflow_execution_id = ? ORDER BY id",
                (execution_id,),
            ).fetchall()
            result = dict(execution)
            result["nodes"] = [dict(row) for row in nodes]
            return result

    def list_executions(self, limit: int = 100) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 1_000))
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM workflow_executions ORDER BY finished_at DESC LIMIT ?",
                (safe_limit,),
            ).fetchall()
            return [dict(row) for row in rows]

    def close(self) -> None:
        with self._lock:
            self._connection.close()

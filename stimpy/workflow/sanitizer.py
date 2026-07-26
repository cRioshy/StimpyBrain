"""Bounded audit serialization with recursive secret and path redaction."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any


SECRET_FRAGMENTS = (
    "token",
    "password",
    "authorization",
    "cookie",
    "secret",
    "api_key",
    "apikey",
)
PATH_FRAGMENTS = ("file_path", "filepath", "local_path", "directory", "workspace_path")


@dataclass(frozen=True)
class AuditSanitizer:
    max_bytes: int = 65_536
    preview_chars: int = 512

    def sanitize(self, value: Any) -> Any:
        clean = self._clean(value)
        encoded = json.dumps(clean, sort_keys=True, ensure_ascii=True, default=str).encode("utf-8")
        if len(encoded) <= self.max_bytes:
            return clean
        return {
            "_audit_type": "oversized_payload",
            "size_bytes": len(encoded),
            "sha256": hashlib.sha256(encoded).hexdigest(),
            "preview": encoded[: self.preview_chars].decode("utf-8", errors="replace"),
        }

    def dumps(self, value: Any) -> str:
        return json.dumps(self.sanitize(value), sort_keys=True, ensure_ascii=True, default=str)

    def _clean(self, value: Any) -> Any:
        if isinstance(value, dict):
            result: dict[str, Any] = {}
            for raw_key, item in value.items():
                key = str(raw_key)
                lowered = key.lower()
                if any(fragment in lowered for fragment in SECRET_FRAGMENTS):
                    result[key] = "[REDACTED]"
                elif any(fragment in lowered for fragment in PATH_FRAGMENTS):
                    result[key] = "[REDACTED_PATH]"
                else:
                    result[key] = self._clean(item)
            return result
        if isinstance(value, (list, tuple)):
            return [self._clean(item) for item in value]
        if isinstance(value, (bytes, bytearray, memoryview)):
            raw = bytes(value)
            return {
                "_audit_type": "binary",
                "size_bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        if isinstance(value, str) and len(value) > self.preview_chars:
            raw = value.encode("utf-8")
            return {
                "_audit_type": "large_text",
                "size_bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "preview": value[: self.preview_chars],
            }
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        return {"_audit_type": "unsupported", "python_type": type(value).__name__}


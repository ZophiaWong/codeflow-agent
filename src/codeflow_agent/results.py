"""Structured tool result contract."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ToolResult:
    ok: bool
    data: Any = None
    summary: str = ""
    error_type: str | None = None
    error_message: str | None = None

    @classmethod
    def success(cls, data: Any = None, summary: str = "") -> "ToolResult":
        return cls(ok=True, data=data, summary=summary)

    @classmethod
    def failure(
        cls,
        error_type: str,
        error_message: str,
        *,
        summary: str = "",
        data: Any = None,
    ) -> "ToolResult":
        return cls(
            ok=False,
            data=data,
            summary=summary,
            error_type=error_type,
            error_message=error_message,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

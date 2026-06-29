from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MemoryledgerError(Exception):
    code: str
    message: str
    details: dict[str, object] | None = None

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


def require(condition: bool, code: str, message: str) -> None:
    if not condition:
        raise MemoryledgerError(code, message)

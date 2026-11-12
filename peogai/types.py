from dataclasses import dataclass
from typing import Any, Callable, Literal

EventSink = Callable[[str, dict[str, Any]], None]


@dataclass(frozen=True)
class Issue:
    id: str
    repo: str
    path: str
    line: int
    end_line: int
    kind: Literal["security", "refactor"]
    rule: str
    message: str


@dataclass(frozen=True)
class Edit:
    old: str
    new: str


@dataclass(frozen=True)
class Proposal:
    explanation: str
    edits: list[Edit]


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    output: str

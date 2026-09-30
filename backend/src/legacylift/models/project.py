"""Project data kept in memory for the first API skeleton."""

from dataclasses import dataclass, field


@dataclass
class SourceFile:
    id: str
    name: str
    kind: str  # program, copybook, or data
    content: str


@dataclass
class Run:
    id: str
    kind: str
    status: str


@dataclass
class Project:
    id: str
    name: str
    files: list[SourceFile] = field(default_factory=list)
    runs: list[Run] = field(default_factory=list)

"""COPY and CALL dependency links between parsed COBOL programs and project files.

Hand-off for the API::

    find_dependencies(programs, catalog) -> (list[Dependency], list[UnresolvedRef])

``catalog`` is the project's file names. Matching ignores case and extension
(``ACCTDEF`` ↔ ``ACCTDEF.cpy``, ``TXNPOST`` ↔ ``TXNPOST.cbl``). References with
no matching file are returned in ``unresolved``.
"""

from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum
from pathlib import PurePosixPath

from pydantic import BaseModel

from legacylift.cobol.parser import ParsedProgram


class DependencyKind(StrEnum):
    """How one program refers to another file."""

    COPY = "copy"
    CALL = "call"


class Dependency(BaseModel):
    """A resolved link from a program to a project file."""

    source: str
    target: str
    kind: DependencyKind
    line: int


class UnresolvedRef(BaseModel):
    """A COPY or CALL whose name does not match any project file."""

    source: str
    name: str
    kind: DependencyKind
    line: int


def _stem(filename: str) -> str:
    """File base name without extension, casefolded for matching."""
    return PurePosixPath(filename.replace("\\", "/")).stem.casefold()


def _catalog_index(catalog: Sequence[str]) -> dict[str, list[str]]:
    """Map casefolded stem → project file names (stable catalog order)."""
    index: dict[str, list[str]] = {}
    for name in catalog:
        index.setdefault(_stem(name), []).append(name)
    return index


def _prefer_target(candidates: list[str], kind: DependencyKind) -> str:
    """Pick the best catalog match for a COPY (prefer ``.cpy``) or CALL (``.cbl``/``.cob``)."""
    if len(candidates) == 1:
        return candidates[0]

    def suffix(name: str) -> str:
        return PurePosixPath(name.replace("\\", "/")).suffix.casefold()

    if kind == DependencyKind.COPY:
        preferred = [n for n in candidates if suffix(n) == ".cpy"]
    else:
        preferred = [n for n in candidates if suffix(n) in {".cbl", ".cob"}]
    return preferred[0] if preferred else candidates[0]


def _resolve(
    name: str,
    kind: DependencyKind,
    index: dict[str, list[str]],
) -> str | None:
    """Return the matched project file name, or ``None`` if unresolved."""
    candidates = index.get(name.casefold())
    if not candidates:
        return None
    return _prefer_target(candidates, kind)


def find_dependencies(
    programs: Sequence[ParsedProgram],
    catalog: Sequence[str],
) -> tuple[list[Dependency], list[UnresolvedRef]]:
    """Build COPY/CALL links from parsed programs against project file names.

    Args:
        programs: Parsed COBOL programs (``ParsedProgram.copies`` / ``.calls``).
        catalog: All project file names used for matching (programs, copybooks, …).

    Returns:
        ``(dependencies, unresolved)`` — resolved edges use the matched file
        name as ``target``; unresolved entries keep the COBOL reference ``name``.
    """
    index = _catalog_index(catalog)
    dependencies: list[Dependency] = []
    unresolved: list[UnresolvedRef] = []

    for program in programs:
        source = program.name
        for copy in program.copies:
            target = _resolve(copy.name, DependencyKind.COPY, index)
            if target is None:
                unresolved.append(
                    UnresolvedRef(
                        source=source,
                        name=copy.name,
                        kind=DependencyKind.COPY,
                        line=copy.line,
                    )
                )
            else:
                dependencies.append(
                    Dependency(
                        source=source,
                        target=target,
                        kind=DependencyKind.COPY,
                        line=copy.line,
                    )
                )
        for call in program.calls:
            target = _resolve(call.name, DependencyKind.CALL, index)
            if target is None:
                unresolved.append(
                    UnresolvedRef(
                        source=source,
                        name=call.name,
                        kind=DependencyKind.CALL,
                        line=call.line,
                    )
                )
            else:
                dependencies.append(
                    Dependency(
                        source=source,
                        target=target,
                        kind=DependencyKind.CALL,
                        line=call.line,
                    )
                )

    return dependencies, unresolved

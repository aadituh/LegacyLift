"""COPY, CALL, and PERFORM dependency links from parsed COBOL programs.

Hand-off for the API::

    find_dependencies(programs, catalog) -> (list[Dependency], list[UnresolvedRef])

* ``copy`` / ``call`` — match names to project files (case/extension ignored);
  unmatched names go in ``unresolved``.
* ``perform`` — paragraph-to-paragraph links inside a program
  (``source`` = ``file:CALLER``, ``target`` = performed paragraph).
  ``PERFORM a THRU b`` expands to every paragraph from ``a`` through ``b``.
  Unknown paragraph names go in ``unresolved``.
"""

from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum
from pathlib import PurePosixPath

from pydantic import BaseModel

from legacylift.cobol.parser import Paragraph, ParsedProgram, PerformRef


class DependencyKind(StrEnum):
    """How one program unit refers to another."""

    COPY = "copy"
    CALL = "call"
    PERFORM = "perform"


class Dependency(BaseModel):
    """A resolved link (file-to-file for COPY/CALL, paragraph-to-paragraph for PERFORM)."""

    source: str
    target: str
    kind: DependencyKind
    line: int


class UnresolvedRef(BaseModel):
    """A COPY, CALL, or PERFORM whose target could not be resolved."""

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


def _resolve_file(
    name: str,
    kind: DependencyKind,
    index: dict[str, list[str]],
) -> str | None:
    """Return the matched project file name, or ``None`` if unresolved."""
    candidates = index.get(name.casefold())
    if not candidates:
        return None
    return _prefer_target(candidates, kind)


def _perform_source(program_name: str, caller: str | None) -> str:
    """Qualify the calling paragraph with its program file name."""
    if caller:
        return f"{program_name}:{caller}"
    return program_name


def _paragraphs_through(
    paragraphs: Sequence[Paragraph], start: str, end: str
) -> list[str] | None:
    """Paragraph names from ``start`` through ``end`` in PROCEDURE order.

    Returns ``None`` if either endpoint is missing.
    """
    names = [p.name for p in paragraphs]
    try:
        i = names.index(start)
        j = names.index(end)
    except ValueError:
        return None
    if i > j:
        i, j = j, i
    return names[i : j + 1]


def _add_perform_links(
    program: ParsedProgram,
    perform: PerformRef,
    dependencies: list[Dependency],
    unresolved: list[UnresolvedRef],
) -> None:
    """Resolve one PERFORM (and optional THRU range) against local paragraphs."""
    source = _perform_source(program.name, perform.caller)
    known = {p.name for p in program.paragraphs}

    if perform.thru:
        span = _paragraphs_through(program.paragraphs, perform.name, perform.thru)
        if span is None:
            for name in (perform.name, perform.thru):
                if name not in known:
                    unresolved.append(
                        UnresolvedRef(
                            source=source,
                            name=name,
                            kind=DependencyKind.PERFORM,
                            line=perform.line,
                        )
                    )
            return
        targets = span
    elif perform.name not in known:
        unresolved.append(
            UnresolvedRef(
                source=source,
                name=perform.name,
                kind=DependencyKind.PERFORM,
                line=perform.line,
            )
        )
        return
    else:
        targets = [perform.name]

    for target in targets:
        dependencies.append(
            Dependency(
                source=source,
                target=target,
                kind=DependencyKind.PERFORM,
                line=perform.line,
            )
        )


def find_dependencies(
    programs: Sequence[ParsedProgram],
    catalog: Sequence[str],
) -> tuple[list[Dependency], list[UnresolvedRef]]:
    """Build COPY/CALL/PERFORM links from parsed programs.

    Args:
        programs: Parsed COBOL programs.
        catalog: Project file names for COPY/CALL matching.

    Returns:
        ``(dependencies, unresolved)``.
    """
    index = _catalog_index(catalog)
    dependencies: list[Dependency] = []
    unresolved: list[UnresolvedRef] = []

    for program in programs:
        source = program.name
        for copy in program.copies:
            target = _resolve_file(copy.name, DependencyKind.COPY, index)
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
            target = _resolve_file(call.name, DependencyKind.CALL, index)
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
        for perform in program.performs:
            _add_perform_links(program, perform, dependencies, unresolved)

    return dependencies, unresolved

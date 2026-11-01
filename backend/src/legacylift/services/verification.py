"""Verify: run COBOL and its generated Python in the runner container and compare.

``verify_project`` checks every main program of a project: it compiles the program
with the programs it calls (``called_programs``), runs it and its Python through a
``Runner`` with the project's ``.dat`` files, and compares stdout
(``compare_outputs``). ``RunnerClient`` is the ``Runner`` that calls the runner
container (``legacylift.runner.server``) over HTTP.
"""

from __future__ import annotations

import difflib
import json
import urllib.error
import urllib.request
from collections.abc import Iterable, Mapping
from typing import Protocol

from legacylift.cobol.dependencies import DependencyKind, find_dependencies
from legacylift.cobol.parser import parse_program
from legacylift.models import (
    ConvertedProjectFile,
    EquivalenceCheck,
    FileKind,
    Project,
    RunStatus,
    SourceFile,
)
from legacylift.runner.sandbox import RunResult

# Covers cobc's compile limit plus the run limit in the runner.
DEFAULT_RUNNER_TIMEOUT_SECONDS = 120.0
RUNNER_OFF = (
    "Verification is off: set LEGACYLIFT_ENABLE_RUNNER=true where the runner container "
    "is available (docker compose up turns it on)."
)


class RunnerError(Exception):
    """The runner could not be reached or sent back something unusable."""


class Runner(Protocol):
    """Where verify runs code: ``RunnerClient``, or a stub in tests."""

    def run_cobol(
        self,
        programs: Mapping[str, str],
        *,
        main: str,
        copybooks: Mapping[str, str],
        data_files: Mapping[str, str],
    ) -> RunResult:
        """Compile ``programs`` with ``main`` first and run it."""

    def run_python(
        self, scripts: Mapping[str, str], *, main: str, data_files: Mapping[str, str]
    ) -> RunResult:
        """Run the ``main`` script."""


class RunnerClient:
    """A ``Runner`` that calls the runner container's ``/run/cobol`` and ``/run/python``.

    Each method raises ``RunnerError`` when the runner is unreachable or rejects
    the request.

    Example:
        >>> RunnerClient("http://runner:8001/").url
        'http://runner:8001'
    """

    def __init__(self, url: str, timeout: float = DEFAULT_RUNNER_TIMEOUT_SECONDS) -> None:
        """Create the client.

        Args:
            url: The runner's base URL, such as ``http://runner:8001``.
            timeout: Seconds to wait for one run, compile included.
        """
        self.url = url.rstrip("/")
        self.timeout = timeout

    def run_cobol(
        self,
        programs: Mapping[str, str],
        *,
        main: str,
        copybooks: Mapping[str, str],
        data_files: Mapping[str, str],
    ) -> RunResult:
        """Compile ``programs`` with ``main`` first and run it in the runner."""
        body: dict[str, object] = {"programs": dict(programs), "main": main}
        body |= {"copybooks": dict(copybooks), "data_files": dict(data_files)}
        return self._post("/run/cobol", body)

    def run_python(
        self, scripts: Mapping[str, str], *, main: str, data_files: Mapping[str, str]
    ) -> RunResult:
        """Run the ``main`` script in the runner."""
        body: dict[str, object] = {"scripts": dict(scripts), "main": main}
        return self._post("/run/python", body | {"data_files": dict(data_files)})

    def _post(self, path: str, body: dict[str, object]) -> RunResult:
        request = urllib.request.Request(
            self.url + path,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return RunResult(**json.load(response))
        except urllib.error.HTTPError as error:
            raise RunnerError(
                f"The runner answered {error.code}: {error.read()[:300]!r}"
            ) from error
        except (OSError, ValueError, TypeError) as error:  # unreachable, timeout, bad JSON
            raise RunnerError(f"The runner at {self.url} could not be reached: {error}") from error


def verify_project(
    runner: Runner | None, project: Project, converted: Iterable[ConvertedProjectFile]
) -> tuple[RunStatus, list[EquivalenceCheck]]:
    """Check each converted main program against its COBOL.

    Programs that another program calls are compiled into their caller and get
    no check of their own.

    Args:
        runner: Where to run code; ``None`` means verify is off.
        project: The project, for its programs, copybooks, and ``.dat`` files.
        converted: The files of the convert run being verified.

    Returns:
        The run status (``verified``, ``mismatch``, or ``not_verified`` when nothing
        could be compared) and one check per main program.
    """
    by_id = {file.id: file for file in project.files}
    programs = {file.name: file for file in project.files if file.kind == FileKind.PROGRAM}
    copybooks = {f.name: f.content for f in project.files if f.kind == FileKind.COPYBOOK}
    data_files = {f.name: f.content for f in project.files if f.kind == FileKind.DATA}
    calls = called_programs(programs.values())
    called = {name for targets in calls.values() for name in targets}

    checks: list[EquivalenceCheck] = []
    compared = False
    for file in converted:
        source = by_id.get(file.source_file_id)
        if source is not None and source.name in called:
            continue
        check = EquivalenceCheck(
            source_name=file.source_name, python_name=file.python_name, equivalent=False
        )
        if source is None or source.kind != FileKind.PROGRAM:
            check.error = f"Source program {file.source_name!r} is missing from the project."
        elif runner is None:
            check.error = RUNNER_OFF
        else:
            sources = {name: programs[name].content for name in [source.name, *calls[source.name]]}
            try:
                _run_both(runner, check, sources, copybooks, data_files, file.python)
                compared = True
            except RunnerError as error:
                check.error = str(error)
        checks.append(check)

    if not compared:
        return RunStatus.NOT_VERIFIED, checks
    if all(check.equivalent for check in checks):
        return RunStatus.VERIFIED, checks
    return RunStatus.MISMATCH, checks


def called_programs(programs: Iterable[SourceFile]) -> dict[str, list[str]]:
    r"""Map each program to the project programs it calls, directly or through others.

    Args:
        programs: The project's COBOL programs.

    Returns:
        Program file name → called program file names, in first-call order.

    Example:
        >>> main = SourceFile(id="1", name="MAIN.cbl", kind="program",
        ...     content='       PROCEDURE DIVISION.\n           CALL "SUB".\n')
        >>> sub = SourceFile(id="2", name="SUB.cbl", kind="program", content="")
        >>> called_programs([main, sub])
        {'MAIN.cbl': ['SUB.cbl'], 'SUB.cbl': []}
    """
    programs = list(programs)
    parsed = [parse_program(program.name, program.content) for program in programs]
    links, _ = find_dependencies(parsed, [program.name for program in programs])
    direct: dict[str, list[str]] = {program.name: [] for program in programs}
    for link in links:
        if link.kind == DependencyKind.CALL and link.target not in direct[link.source]:
            direct[link.source].append(link.target)

    def reachable(name: str) -> list[str]:
        found: list[str] = []
        pending = list(direct[name])
        while pending:
            target = pending.pop(0)
            if target != name and target not in found:
                found.append(target)
                pending.extend(direct[target])
        return found

    return {name: reachable(name) for name in direct}


def compare_outputs(cobol: str, python: str) -> tuple[bool, str]:
    r"""Compare two outputs exactly, apart from ``\r\n`` versus ``\n``.

    Args:
        cobol: What the COBOL program printed.
        python: What the Python printed.

    Returns:
        ``(True, "")`` when they match, else ``(False, diff)`` with a unified diff
        from ``cobol`` to ``python``.

    Example:
        >>> compare_outputs("A\r\nB\n", "A\nB\n")
        (True, '')
        >>> print(compare_outputs("A\nB\n", "A\nC\n")[1])
        --- cobol
        +++ python
        @@ -1,2 +1,2 @@
         A
        -B
        +C
    """
    cobol = cobol.replace("\r\n", "\n")
    python = python.replace("\r\n", "\n")
    if cobol == python:
        return True, ""
    lines = difflib.unified_diff(
        cobol.splitlines(), python.splitlines(), fromfile="cobol", tofile="python", lineterm=""
    )
    return False, "\n".join(lines) or "The outputs differ only in the line break at the end."


def _run_both(
    runner: Runner,
    check: EquivalenceCheck,
    sources: dict[str, str],
    copybooks: dict[str, str],
    data_files: dict[str, str],
    python: str,
) -> None:
    """Run the COBOL (first of ``sources`` is the main program) and the Python; fill in ``check``."""
    main = next(iter(sources))
    cobol = runner.run_cobol(sources, main=main, copybooks=copybooks, data_files=data_files)
    check.cobol_stdout = cobol.stdout
    if cobol.stage == "compile":
        check.error = f"The COBOL did not compile:\n{cobol.stderr.strip()}"
        return
    name = check.python_name
    result = runner.run_python({name: python}, main=name, data_files=data_files)
    check.python_stdout = result.stdout
    same, check.diff = compare_outputs(cobol.stdout, result.stdout)
    failures = [_failure("COBOL", cobol), _failure("Python", result)]
    check.error = "\n".join(failure for failure in failures if failure) or None
    check.equivalent = same and check.error is None
    if check.error is None and not same:
        check.error = "The outputs differ."


def _failure(language: str, result: RunResult) -> str:
    """Why a run did not finish cleanly, or ``""`` if it did."""
    if result.timed_out:
        return f"{language} was stopped at the time limit."
    if result.output_truncated:
        return f"{language} was stopped at the output limit."
    if result.exit_code != 0:
        detail = result.stderr.strip()[-1000:]
        return f"{language} exited with code {result.exit_code}." + (
            f"\n{detail}" if detail else ""
        )
    return ""

"""Compile and run COBOL with GnuCOBOL (``cobc``).

Used by functional-equivalence checks: the COBOL program is compiled in a
temporary directory, executed, and its stdout is returned for comparison with
generated Python.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import NamedTuple

# Prefer an explicit path from settings/env; otherwise search PATH.
COBC_ENV = "LEGACYLIFT_COBC_PATH"
DEFAULT_TIMEOUT_SECONDS = 15.0


class CobolRunResult(NamedTuple):
    """Outcome of compiling and running one COBOL program.

    Attributes:
        ok: ``True`` when the program compiled and exited with status 0.
        stdout: Captured standard output (may be partial on failure).
        stderr: Compiler or runtime error text.
        returncode: Process exit code, or ``None`` if ``cobc`` was not found.
    """

    ok: bool
    stdout: str
    stderr: str
    returncode: int | None


def find_cobc(explicit_path: str | None = None) -> str | None:
    """Locate the GnuCOBOL compiler.

    Args:
        explicit_path: Optional absolute/relative path to ``cobc``.

    Returns:
        The path to ``cobc``, or ``None`` if it is not available.
    """
    candidates = [
        explicit_path,
        os.environ.get(COBC_ENV),
        shutil.which("cobc"),
    ]
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate)
        if path.is_file():
            return str(path.resolve())
        found = shutil.which(candidate)
        if found:
            return found
    return None


def cobc_available(explicit_path: str | None = None) -> bool:
    """Return whether GnuCOBOL's ``cobc`` can be invoked."""
    return find_cobc(explicit_path) is not None


def run_cobol(
    source: str,
    *,
    source_name: str = "program.cbl",
    copybooks: dict[str, str] | None = None,
    stdin_data: str = "",
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    cobc_path: str | None = None,
) -> CobolRunResult:
    """Compile ``source`` with GnuCOBOL and run the resulting program.

    Writes the program and any copybooks into a temporary directory, compiles
    with ``cobc -x -free``, then executes the binary with optional stdin.

    Args:
        source: Full COBOL program text.
        source_name: File name used on disk (extension should be ``.cbl``/``.cob``).
        copybooks: Optional map of copybook file name → contents (for ``COPY``).
        stdin_data: Text fed to the program's standard input.
        timeout: Seconds allowed for compile and for run, each.
        cobc_path: Optional path to ``cobc`` (else ``LEGACYLIFT_COBC_PATH`` / PATH).

    Returns:
        A ``CobolRunResult``. If ``cobc`` is missing, ``ok`` is ``False`` and
        ``returncode`` is ``None``.
    """
    cobc = find_cobc(cobc_path)
    if cobc is None:
        return CobolRunResult(
            ok=False,
            stdout="",
            stderr=(
                "GnuCOBOL (cobc) was not found. Install GnuCOBOL and ensure "
                "cobc is on PATH, or set LEGACYLIFT_COBC_PATH."
            ),
            returncode=None,
        )

    stem = Path(source_name).stem or "program"
    with tempfile.TemporaryDirectory(prefix="legacylift-cobol-") as tmp:
        work = Path(tmp)
        source_path = work / Path(source_name).name
        source_path.write_text(source, encoding="utf-8", newline="\n")
        for name, content in (copybooks or {}).items():
            (work / Path(name).name).write_text(content, encoding="utf-8", newline="\n")

        # Windows gets .exe; Unix cobc writes the stem with no extension.
        binary = work / (stem + (".exe" if os.name == "nt" else ""))
        compile_cmd = [
            cobc,
            "-x",
            "-free",
            "-o",
            str(binary),
            str(source_path),
        ]
        try:
            compiled = subprocess.run(
                compile_cmd,
                cwd=work,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return CobolRunResult(
                ok=False,
                stdout="",
                stderr=f"cobc timed out after {timeout}s while compiling {source_name}.",
                returncode=None,
            )
        except OSError as error:
            return CobolRunResult(
                ok=False,
                stdout="",
                stderr=f"Failed to run cobc: {error}",
                returncode=None,
            )

        if compiled.returncode != 0 or not binary.is_file():
            detail = (compiled.stderr or compiled.stdout or "compile failed").strip()
            return CobolRunResult(
                ok=False,
                stdout=compiled.stdout,
                stderr=detail,
                returncode=compiled.returncode,
            )

        try:
            ran = subprocess.run(
                [str(binary)],
                cwd=work,
                input=stdin_data,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return CobolRunResult(
                ok=False,
                stdout="",
                stderr=f"Program timed out after {timeout}s: {source_name}.",
                returncode=None,
            )
        except OSError as error:
            return CobolRunResult(
                ok=False,
                stdout="",
                stderr=f"Failed to execute compiled COBOL: {error}",
                returncode=None,
            )

        return CobolRunResult(
            ok=ran.returncode == 0,
            stdout=ran.stdout,
            stderr=ran.stderr,
            returncode=ran.returncode,
        )

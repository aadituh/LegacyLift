"""Compare GnuCOBOL program output with generated Python for equivalence.

``check_functional_equivalence`` runs one COBOL source under GnuCOBOL and the
matching Python draft, then requires stdout to match exactly.
"""

from __future__ import annotations

import contextlib
import io
from typing import NamedTuple

from legacylift.cobol.gnucobol import cobc_available, run_cobol


class EquivalenceResult(NamedTuple):
    """Per-program COBOL-versus-Python comparison.

    Attributes:
        source_name: COBOL file name.
        python_name: Generated Python file name.
        equivalent: ``True`` when both sides ran and stdout matched exactly.
        cobol_stdout: Output from the compiled COBOL program.
        python_stdout: Output from the generated Python script.
        error: Problem description when not equivalent (or tooling missing).
        cobc_available: Whether GnuCOBOL was found for this check.
    """

    source_name: str
    python_name: str
    equivalent: bool
    cobol_stdout: str
    python_stdout: str
    error: str | None
    cobc_available: bool


def run_python_capture(python: str) -> tuple[str, str | None]:
    """Execute generated Python as ``__main__`` and return stdout or an error.

    Args:
        python: Full Python script text.

    Returns:
        ``(stdout, None)`` on success, or ``("", error_message)`` on failure.
    """
    try:
        compiled = compile(python, "<generated>", "exec")
    except SyntaxError as error:
        return "", f"Python SyntaxError: {error.msg} (line {error.lineno})"

    buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(buffer):
            exec(compiled, {"__name__": "__main__"})  # noqa: S102
    except Exception as error:  # noqa: BLE001 - surface any runtime failure
        return buffer.getvalue(), f"Python {type(error).__name__}: {error}"
    return buffer.getvalue(), None


def check_functional_equivalence(
    *,
    source_name: str,
    python_name: str,
    cobol_source: str,
    python_source: str,
    copybooks: dict[str, str] | None = None,
    stdin_data: str = "",
    cobc_path: str | None = None,
) -> EquivalenceResult:
    """Run COBOL (GnuCOBOL) and Python; require identical stdout.

    Args:
        source_name: COBOL file name (for messages and temp file naming).
        python_name: Python file name (for the result record).
        cobol_source: Full COBOL program text.
        python_source: Generated Python script text.
        copybooks: Optional COPY book name → text map.
        stdin_data: Shared stdin for both runs (usually empty).
        cobc_path: Optional path to ``cobc``.

    Returns:
        An ``EquivalenceResult``. If GnuCOBOL is missing, ``equivalent`` is
        ``False``, ``cobc_available`` is ``False``, and ``error`` explains how
        to install it.
    """
    available = cobc_available(cobc_path)
    if not available:
        return EquivalenceResult(
            source_name=source_name,
            python_name=python_name,
            equivalent=False,
            cobol_stdout="",
            python_stdout="",
            error=(
                "GnuCOBOL (cobc) was not found. Install GnuCOBOL and ensure "
                "cobc is on PATH, or set LEGACYLIFT_COBC_PATH."
            ),
            cobc_available=False,
        )

    cobol = run_cobol(
        cobol_source,
        source_name=source_name,
        copybooks=copybooks,
        stdin_data=stdin_data,
        cobc_path=cobc_path,
    )
    python_stdout, python_error = run_python_capture(python_source)

    if not cobol.ok:
        return EquivalenceResult(
            source_name=source_name,
            python_name=python_name,
            equivalent=False,
            cobol_stdout=cobol.stdout,
            python_stdout=python_stdout,
            error=f"COBOL run failed: {cobol.stderr or f'exit {cobol.returncode}'}",
            cobc_available=True,
        )
    if python_error is not None:
        return EquivalenceResult(
            source_name=source_name,
            python_name=python_name,
            equivalent=False,
            cobol_stdout=cobol.stdout,
            python_stdout=python_stdout,
            error=python_error,
            cobc_available=True,
        )
    if cobol.stdout != python_stdout:
        return EquivalenceResult(
            source_name=source_name,
            python_name=python_name,
            equivalent=False,
            cobol_stdout=cobol.stdout,
            python_stdout=python_stdout,
            error=(
                "Output mismatch.\n"
                f"COBOL:  {cobol.stdout!r}\n"
                f"Python: {python_stdout!r}"
            ),
            cobc_available=True,
        )
    return EquivalenceResult(
        source_name=source_name,
        python_name=python_name,
        equivalent=True,
        cobol_stdout=cobol.stdout,
        python_stdout=python_stdout,
        error=None,
        cobc_available=True,
    )

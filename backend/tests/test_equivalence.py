"""GnuCOBOL runner and COBOL-versus-Python equivalence checks."""

from unittest.mock import patch

import pytest

from legacylift.cobol.converter import translate_program
from legacylift.cobol.equivalence import check_functional_equivalence, run_python_capture
from legacylift.cobol.gnucobol import CobolRunResult, cobc_available, find_cobc, run_cobol

from helpers import HELLO

SIMPLE = """IDENTIFICATION DIVISION.
PROGRAM-ID. HI.
DATA DIVISION.
WORKING-STORAGE SECTION.
PROCEDURE DIVISION.
DISPLAY "ok".
STOP RUN.
"""


def test_run_python_capture_returns_stdout():
    stdout, error = run_python_capture("print('hi')\n")
    assert error is None
    assert stdout == "hi\n"


def test_run_python_capture_reports_syntax_errors():
    stdout, error = run_python_capture("def main(:\n")
    assert stdout == ""
    assert error is not None
    assert "SyntaxError" in error


def test_find_cobc_respects_explicit_missing_path():
    assert find_cobc("/definitely/not/a/real/cobc-binary") is None


def test_check_equivalence_reports_missing_cobc():
    draft = translate_program(SIMPLE)
    with patch("legacylift.cobol.equivalence.cobc_available", return_value=False):
        result = check_functional_equivalence(
            source_name="hi.cbl",
            python_name="hi.py",
            cobol_source=SIMPLE,
            python_source=draft.python,
        )
    assert result.equivalent is False
    assert result.cobc_available is False
    assert result.error is not None
    assert "cobc" in result.error.lower() and "not found" in result.error.lower()


def test_check_equivalence_passes_when_outputs_match():
    draft = translate_program(SIMPLE)
    fake_cobol = CobolRunResult(ok=True, stdout="ok\n", stderr="", returncode=0)
    with (
        patch("legacylift.cobol.equivalence.cobc_available", return_value=True),
        patch("legacylift.cobol.equivalence.run_cobol", return_value=fake_cobol),
    ):
        result = check_functional_equivalence(
            source_name="hi.cbl",
            python_name="hi.py",
            cobol_source=SIMPLE,
            python_source=draft.python,
        )
    assert result.equivalent is True
    assert result.cobol_stdout == result.python_stdout == "ok\n"
    assert result.error is None


def test_check_equivalence_detects_output_mismatch():
    draft = translate_program(SIMPLE)
    fake_cobol = CobolRunResult(ok=True, stdout="different\n", stderr="", returncode=0)
    with (
        patch("legacylift.cobol.equivalence.cobc_available", return_value=True),
        patch("legacylift.cobol.equivalence.run_cobol", return_value=fake_cobol),
    ):
        result = check_functional_equivalence(
            source_name="hi.cbl",
            python_name="hi.py",
            cobol_source=SIMPLE,
            python_source=draft.python,
        )
    assert result.equivalent is False
    assert "Output mismatch" in (result.error or "")


def test_check_equivalence_reports_cobol_compile_failure():
    draft = translate_program(SIMPLE)
    fake_cobol = CobolRunResult(ok=False, stdout="", stderr="error: syntax", returncode=1)
    with (
        patch("legacylift.cobol.equivalence.cobc_available", return_value=True),
        patch("legacylift.cobol.equivalence.run_cobol", return_value=fake_cobol),
    ):
        result = check_functional_equivalence(
            source_name="hi.cbl",
            python_name="hi.py",
            cobol_source=SIMPLE,
            python_source=draft.python,
        )
    assert result.equivalent is False
    assert "COBOL run failed" in (result.error or "")


@pytest.mark.skipif(not cobc_available(), reason="GnuCOBOL (cobc) not installed")
def test_real_gnucobol_matches_python_for_hello():
    draft = translate_program(HELLO)
    cobol = run_cobol(HELLO, source_name="hello.cbl")
    assert cobol.ok, cobol.stderr
    result = check_functional_equivalence(
        source_name="hello.cbl",
        python_name="hello.py",
        cobol_source=HELLO,
        python_source=draft.python,
    )
    assert result.equivalent is True
    assert result.cobol_stdout == result.python_stdout

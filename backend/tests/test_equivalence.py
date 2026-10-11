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


def test_project_verify_without_cobc_is_not_verified(client, tmp_path):
    created = client.post("/api/projects", json={"name": "V"}).json()
    base = f"/api/projects/{created['id']}"
    client.post(f"{base}/files", files=[("files", ("hello.cbl", HELLO))])
    assert client.post(f"{base}/convert").status_code == 200
    with patch("legacylift.cobol.equivalence.cobc_available", return_value=False):
        response = client.post(f"{base}/verify")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "not_verified"
    assert body["passed"] is None
    assert body["files"]
    assert "cobc" in body["note"].lower()


def test_project_verify_reports_verified_when_outputs_match(client):
    created = client.post("/api/projects", json={"name": "V"}).json()
    base = f"/api/projects/{created['id']}"
    client.post(f"{base}/files", files=[("files", ("hello.cbl", HELLO))])
    converted = client.post(f"{base}/convert").json()
    python_out = "Hello, LegacyLift\nDemo count: 2\n"
    fake_cobol = CobolRunResult(ok=True, stdout=python_out, stderr="", returncode=0)
    with (
        patch("legacylift.cobol.equivalence.cobc_available", return_value=True),
        patch("legacylift.cobol.equivalence.run_cobol", return_value=fake_cobol),
    ):
        response = client.post(f"{base}/verify")
    body = response.json()
    assert body["status"] == "verified"
    assert body["passed"] is True
    assert body["files"][0]["equivalent"] is True
    assert body["files"][0]["cobol_stdout"] == python_out
    assert converted["files"][0]["python_name"] == body["files"][0]["python_name"]


def test_project_verify_reports_mismatch(client):
    created = client.post("/api/projects", json={"name": "V"}).json()
    base = f"/api/projects/{created['id']}"
    client.post(f"{base}/files", files=[("files", ("hello.cbl", HELLO))])
    client.post(f"{base}/convert")
    fake_cobol = CobolRunResult(ok=True, stdout="nope\n", stderr="", returncode=0)
    with (
        patch("legacylift.cobol.equivalence.cobc_available", return_value=True),
        patch("legacylift.cobol.equivalence.run_cobol", return_value=fake_cobol),
    ):
        body = client.post(f"{base}/verify").json()
    assert body["status"] == "mismatch"
    assert body["passed"] is False
    assert body["files"][0]["equivalent"] is False


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

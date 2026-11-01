"""The runner: sandboxed COBOL and Python runs, and its HTTP server."""

import json
import shutil
import threading
import urllib.error
import urllib.request
from collections.abc import Iterator
from pathlib import Path

import pytest

from legacylift.runner.sandbox import Limits, RunnerInputError, run_cobol, run_python
from legacylift.runner.server import make_server

DATA = Path(__file__).resolve().parents[1] / "src" / "legacylift" / "data"
FAST = Limits(timeout_seconds=2, compile_timeout_seconds=60, max_output_bytes=1_000)

needs_cobc = pytest.mark.skipif(shutil.which("cobc") is None, reason="GnuCOBOL is not installed")


def sample(*names: str) -> dict[str, str]:
    return {name: (DATA / name).read_text(encoding="utf-8") for name in names}


# --- Python ---


def test_python_reads_data_files_from_its_folder():
    script = "print(open('in.dat').read().strip())"
    result = run_python({"m.py": script}, main="m.py", data_files={"in.dat": "abc\r\n"})
    assert result.ok
    assert result.stdout == "abc\n"


def test_data_files_may_share_a_name_with_the_runner_folders():
    script = "print(open('bin').read() + open('src').read())"
    result = run_python({"m.py": script}, main="m.py", data_files={"bin": "a", "src": "b"})
    assert result.stdout == "ab\n"


def test_python_error_keeps_exit_code_and_stderr():
    result = run_python({"m.py": "print('before')\nraise SystemExit(3)"}, main="m.py")
    assert not result.ok
    assert result.exit_code == 3
    assert result.stdout == "before\n"


def test_python_endless_loop_is_stopped():
    result = run_python({"m.py": "while True:\n    pass"}, main="m.py", limits=FAST)
    assert not result.ok
    assert result.timed_out
    assert result.exit_code is None


def test_python_endless_output_is_cut_at_the_limit():
    result = run_python({"m.py": "while True:\n    print('x' * 99)"}, main="m.py", limits=FAST)
    assert not result.ok
    assert result.output_truncated
    assert len(result.stdout.encode()) <= FAST.max_output_bytes


def test_python_does_not_see_the_api_environment(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://secret")
    script = "import os; print(os.environ.get('DATABASE_URL'))"
    assert run_python({"m.py": script}, main="m.py").stdout == "None\n"


@pytest.mark.parametrize("name", ["../m.py", "/tmp/m.py", ".hidden", "a b.py", ""])
def test_bad_file_names_are_rejected(name: str):
    with pytest.raises(RunnerInputError):
        run_python({name: "print(1)"}, main=name)


def test_main_must_be_one_of_the_files():
    with pytest.raises(RunnerInputError):
        run_python({"m.py": "print(1)"}, main="other.py")


# --- COBOL (needs GnuCOBOL; runs in CI and in the runner image) ---


@needs_cobc
def test_cobol_feesched_runs():
    result = run_cobol(sample("FEESCHED.cbl"), main="FEESCHED.cbl")
    assert result.ok, result.stderr
    assert result.stdout.splitlines()[1] == "OVERDRAFT FEE: 035"


@needs_cobc
def test_cobol_bankmain_runs_with_its_callees_copybooks_and_data():
    result = run_cobol(
        sample("BANKMAIN.cbl", "TXNPOST.cbl", "INTCALC.cbl"),
        main="BANKMAIN.cbl",
        copybooks=sample("ACCTDEF.cpy", "TXNDEF.cpy"),
        data_files=sample("accounts.dat", "transactions.dat"),
    )
    assert result.ok, result.stderr
    assert result.stdout.splitlines()[-1] == "TOTAL INTEREST:            48.29"


@needs_cobc
def test_cobol_compile_error_returns_the_message():
    broken = "       IDENTIFICATION DIVISION.\n       PROGRAM-ID. BROKEN.\n"
    broken += "       PROCEDURE DIVISION.\n           MOVE 1 TO NOWHERE.\n"
    result = run_cobol({"BROKEN.cbl": broken}, main="BROKEN.cbl")
    assert not result.ok
    assert result.stage == "compile"
    assert result.stderr.startswith("BROKEN.cbl:4: error: 'NOWHERE'")


@needs_cobc
def test_cobol_endless_loop_is_stopped():
    looper = "       IDENTIFICATION DIVISION.\n       PROGRAM-ID. LOOPER.\n"
    looper += "       PROCEDURE DIVISION.\n           PERFORM UNTIL 1 = 2\n"
    looper += "               CONTINUE\n           END-PERFORM.\n"
    result = run_cobol({"LOOPER.cbl": looper}, main="LOOPER.cbl", limits=FAST)
    assert result.stage == "run"
    assert result.timed_out


# --- HTTP server ---


@pytest.fixture
def runner_url() -> Iterator[str]:
    server = make_server("127.0.0.1", 0, limits=FAST, max_request_bytes=10_000)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()


def post(url: str, body: object) -> tuple[int, dict[str, object]]:
    data = json.dumps(body).encode()
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, json.load(error)


def test_server_runs_python(runner_url: str):
    status, body = post(
        runner_url + "/run/python", {"scripts": {"m.py": "print(2)"}, "main": "m.py"}
    )
    assert status == 200
    assert body["ok"] is True
    assert body["stdout"] == "2\n"
    assert set(body) == {
        "ok",
        "stage",
        "exit_code",
        "stdout",
        "stderr",
        "timed_out",
        "output_truncated",
    }


@pytest.mark.parametrize(
    "body",
    [
        {"main": "m.py"},
        {"scripts": {"m.py": 1}, "main": "m.py"},
        {"scripts": {"m.py": "print(1)"}},
        {"scripts": {"../m.py": "print(1)"}, "main": "../m.py"},
        [],
    ],
)
def test_server_rejects_bad_bodies(runner_url: str, body: object):
    status, response = post(runner_url + "/run/python", body)
    assert status == 400
    assert response["detail"]


def test_server_rejects_large_bodies(runner_url: str):
    big = {"scripts": {"m.py": "#" * 20_000}, "main": "m.py"}
    assert post(runner_url + "/run/python", big)[0] == 413


def test_server_answers_500_when_a_run_breaks(runner_url: str, monkeypatch: pytest.MonkeyPatch):
    def broken(*args: object, **kwargs: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr("legacylift.runner.server.run_python", broken)
    status, body = post(runner_url + "/run/python", {"scripts": {"m.py": ""}, "main": "m.py"})
    assert (status, body) == (500, {"detail": "Runner error: disk full"})


def test_server_unknown_route_is_404(runner_url: str):
    assert post(runner_url + "/run/java", {})[0] == 404

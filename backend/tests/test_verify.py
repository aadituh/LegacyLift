"""Verify: COBOL and generated Python run in the runner, outputs compared with a diff.

The runner is stubbed: COBOL runs return recorded GnuCOBOL output
(tests/data/recorded/), and Python runs happen locally through the sandbox.
"""

import threading
from collections.abc import Iterator, Mapping
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from legacylift.runner.sandbox import RunResult, run_python
from legacylift.runner.server import make_server
from legacylift.services.verification import RunnerClient, RunnerError, compare_outputs

from helpers import HELLO

BACKEND = Path(__file__).resolve().parents[1]
SAMPLE = BACKEND / "src" / "legacylift" / "data"
RECORDED = BACKEND / "tests" / "data" / "recorded"
BANK_FILES = [
    "BANKMAIN.cbl",
    "TXNPOST.cbl",
    "INTCALC.cbl",
    "FEESCHED.cbl",
    "ACCTDEF.cpy",
    "TXNDEF.cpy",
    "accounts.dat",
    "transactions.dat",
]


def printed(stdout: str) -> RunResult:
    return RunResult(ok=True, stage="run", exit_code=0, stdout=stdout, stderr="")


class FakeRunner:
    """Answers COBOL runs from a table; runs the Python for real."""

    def __init__(self, cobol: Mapping[str, RunResult]) -> None:
        self.cobol = cobol
        self.cobol_runs: list[dict[str, object]] = []
        self.python_runs: list[dict[str, object]] = []

    def run_cobol(self, programs, *, main, copybooks, data_files) -> RunResult:
        self.cobol_runs.append(
            {"programs": list(programs), "main": main, "copybooks": list(copybooks)}
            | {"data_files": list(data_files)}
        )
        return self.cobol[main]

    def run_python(self, scripts, *, main, data_files) -> RunResult:
        self.python_runs.append({"main": main, "data_files": list(data_files)})
        return run_python(scripts, main=main, data_files=data_files)


def project_with(client: TestClient, files: list[tuple[str, str]]) -> str:
    """Create a project, upload the files, convert, and return its base URL."""
    created = client.post("/api/projects", json={"name": "Verify"}).json()
    base = f"/api/projects/{created['id']}"
    uploaded = client.post(f"{base}/files", files=[("files", file) for file in files])
    assert uploaded.status_code == 200, uploaded.json()
    assert client.post(f"{base}/convert").status_code == 200
    return base


def use_runner(client: TestClient, runner: object) -> None:
    client.app.state.project_service.runner = runner  # type: ignore[attr-defined]


def sample(*names: str) -> list[tuple[str, str]]:
    return [(name, (SAMPLE / name).read_text(encoding="utf-8")) for name in names]


def test_verify_is_off_unless_the_setting_turns_it_on(client: TestClient):
    base = project_with(client, [("hello.cbl", HELLO)])
    body = client.post(f"{base}/verify").json()
    assert (body["status"], body["passed"]) == ("not_verified", None)
    assert "LEGACYLIFT_ENABLE_RUNNER" in body["note"]
    assert body["files"][0]["error"] == body["note"].removeprefix("Outputs were not compared. ")


def test_sample_bank_feesched_verifies_and_bankmain_shows_a_diff(client: TestClient):
    runner = FakeRunner(
        {
            "BANKMAIN.cbl": printed((RECORDED / "bank" / "sample" / "BANKMAIN.out").read_text()),
            "FEESCHED.cbl": printed((RECORDED / "FEESCHED.out").read_text()),
        }
    )
    use_runner(client, runner)
    base = project_with(client, sample(*BANK_FILES))

    body = client.post(f"{base}/verify").json()

    assert (body["status"], body["passed"]) == ("mismatch", False)
    bankmain, feesched = body["files"]  # TXNPOST and INTCALC run inside BANKMAIN
    assert (feesched["source_name"], feesched["equivalent"], feesched["diff"]) == (
        "FEESCHED.cbl",
        True,
        "",
    )
    assert feesched["python_stdout"] == feesched["cobol_stdout"]
    assert bankmain["source_name"] == "BANKMAIN.cbl"
    assert bankmain["equivalent"] is False
    assert bankmain["diff"].startswith("--- cobol\n+++ python\n")
    assert bankmain["error"]  # what differs, or how the draft failed
    assert runner.cobol_runs[0] == {
        "programs": ["BANKMAIN.cbl", "TXNPOST.cbl", "INTCALC.cbl"],
        "main": "BANKMAIN.cbl",
        "copybooks": ["ACCTDEF.cpy", "TXNDEF.cpy"],
        "data_files": ["accounts.dat", "transactions.dat"],
    }
    assert runner.python_runs[0] == {
        "main": "BANKMAIN.py",
        "data_files": ["accounts.dat", "transactions.dat"],
    }
    [run] = [run for run in client.get(f"{base}/runs").json()["runs"] if run["kind"] == "verify"]
    assert client.get(f"{base}/runs/{run['id']}").json()["checks"][0]["diff"] == bankmain["diff"]


def test_verified_when_every_program_prints_the_same(client: TestClient):
    use_runner(
        client, FakeRunner({"FEESCHED.cbl": printed((RECORDED / "FEESCHED.out").read_text())})
    )
    base = project_with(client, sample("FEESCHED.cbl"))
    body = client.post(f"{base}/verify").json()
    assert (body["status"], body["passed"]) == ("verified", True)
    assert body["note"] == "COBOL and Python outputs matched for every program."


def test_walkthrough_files_verify_monthend_and_feesched(client: TestClient):
    """docs/walkthrough.md: upload every file in src/legacylift/data/ at once."""
    names = sorted(
        path.name for path in SAMPLE.iterdir() if path.suffix in {".cbl", ".cpy", ".dat"}
    )
    assert len(names) == 10  # the most one project holds
    use_runner(
        client,
        FakeRunner(
            {
                "BANKMAIN.cbl": printed(
                    (RECORDED / "bank" / "sample" / "BANKMAIN.out").read_text()
                ),
                "FEESCHED.cbl": printed((RECORDED / "FEESCHED.out").read_text()),
                "MONTHEND.cbl": printed((RECORDED / "MONTHEND.out").read_text()),
            }
        ),
    )
    base = project_with(client, sample(*names))
    body = client.post(f"{base}/verify").json()
    assert {file["source_name"]: file["equivalent"] for file in body["files"]} == {
        "BANKMAIN.cbl": False,
        "FEESCHED.cbl": True,
        "MONTHEND.cbl": True,
    }


def test_compile_error_is_a_mismatch_with_the_message(client: TestClient):
    failed = RunResult(False, "compile", 1, "", "hello.cbl:3: error: syntax error\n")
    use_runner(client, FakeRunner({"hello.cbl": failed}))
    base = project_with(client, [("hello.cbl", HELLO)])
    body = client.post(f"{base}/verify").json()
    assert (body["status"], body["passed"]) == ("mismatch", False)
    assert (
        body["files"][0]["error"] == "The COBOL did not compile:\nhello.cbl:3: error: syntax error"
    )


def test_cobol_stopped_at_the_time_limit_is_a_mismatch(client: TestClient):
    stopped = RunResult(False, "run", None, "", "", timed_out=True)
    use_runner(client, FakeRunner({"hello.cbl": stopped}))
    base = project_with(client, [("hello.cbl", HELLO)])
    check = client.post(f"{base}/verify").json()["files"][0]
    assert check["equivalent"] is False
    assert check["error"] == "COBOL was stopped at the time limit."


def test_unreachable_runner_is_not_verified(client: TestClient):
    use_runner(client, RunnerClient("http://127.0.0.1:9", timeout=2))
    base = project_with(client, [("hello.cbl", HELLO)])
    body = client.post(f"{base}/verify").json()
    assert (body["status"], body["passed"]) == ("not_verified", None)
    assert "could not be reached" in body["files"][0]["error"]


# --- RunnerClient against a real runner server ---


@pytest.fixture
def runner_url() -> Iterator[str]:
    server = make_server("127.0.0.1", 0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()


def test_runner_client_runs_python_in_the_runner(runner_url: str):
    result = RunnerClient(runner_url).run_python(
        {"m.py": "print(open('a.dat').read().strip())"}, main="m.py", data_files={"a.dat": "42"}
    )
    assert (result.ok, result.stdout) == (True, "42\n")


def test_runner_client_turns_a_rejected_request_into_runner_error(runner_url: str):
    with pytest.raises(RunnerError, match="400"):
        RunnerClient(runner_url).run_python({"../m.py": ""}, main="../m.py", data_files={})


# --- compare_outputs ---


@pytest.mark.parametrize(
    ("cobol", "python", "same"),
    [
        ("A  \nB\n", "A  \nB\n", True),
        ("A\r\nB\r\n", "A\nB\n", True),
        ("A  \n", "A\n", False),  # trailing spaces count
        ("035\n", "35\n", False),
    ],
)
def test_compare_outputs(cobol: str, python: str, same: bool):
    assert compare_outputs(cobol, python)[0] is same


def test_compare_outputs_explains_a_missing_final_line_break():
    assert compare_outputs("A\n", "A") == (
        False,
        "The outputs differ only in the line break at the end.",
    )

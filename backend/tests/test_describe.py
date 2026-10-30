"""Prompt text and describe route for the sample bank. No model call."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from legacylift.cobol.dependencies import find_dependencies
from legacylift.cobol.describe import build_prompt, describe_map
from legacylift.cobol.parser import parse_program
from legacylift.errors import ProjectStateError

from helpers import make_client

DATA = Path(__file__).parents[1] / "src" / "legacylift" / "data"


def test_bank_prompt_names_programs_and_data() -> None:
    names = (
        "BANKMAIN.cbl",
        "TXNPOST.cbl",
        "INTCALC.cbl",
        "ACCTDEF.cpy",
        "TXNDEF.cpy",
        "accounts.dat",
        "transactions.dat",
    )
    programs = [
        parse_program(name, (DATA / name).read_text(encoding="utf-8"))
        for name in names
        if name.endswith((".cbl", ".cob"))
    ]
    dependencies, unresolved = find_dependencies(programs, names)
    prompt = build_prompt(programs, dependencies, unresolved, names)

    for needle in ("BANKMAIN", "TXNPOST", "INTCALC", "ACCTDEF", "accounts.dat"):
        assert needle in prompt


FAKE_MAP = (
    '{"programs": [{"name": "BANKMAIN.cbl", "summary": "Nightly batch."}], '
    '"shared_data": "They share ACCTDEF."}'
)


def _bank_program():
    return parse_program("BANKMAIN.cbl", (DATA / "BANKMAIN.cbl").read_text(encoding="utf-8"))


def test_describe_map_requires_api_key() -> None:
    def fail(prompt: str, api_key: str) -> str:
        raise AssertionError("Gemini was called")

    with pytest.raises(ProjectStateError, match="LEGACYLIFT_GEMINI_API_KEY"):
        describe_map([_bank_program()], ["BANKMAIN.cbl"], api_key=None, complete_prompt=fail)


def test_describe_map_reads_model_json() -> None:
    described = describe_map(
        [_bank_program()],
        ["BANKMAIN.cbl"],
        api_key="test-key",
        complete_prompt=lambda prompt, api_key: FAKE_MAP,
    )
    assert described.programs[0].name == "BANKMAIN.cbl"
    assert described.shared_data == "They share ACCTDEF."


@pytest.fixture
def client_with_key(tmp_path: Path) -> TestClient:
    return make_client(tmp_path, gemini_api_key="test-key")


def _upload_bank(client: TestClient) -> str:
    created = client.post("/api/projects", json={"name": "Bank"}).json()
    base = f"/api/projects/{created['id']}"
    names = ("BANKMAIN.cbl", "TXNPOST.cbl", "INTCALC.cbl", "ACCTDEF.cpy", "accounts.dat")
    files = [(name, (DATA / name).read_text(encoding="utf-8")) for name in names]
    upload = client.post(f"{base}/files", files=[("files", file) for file in files])
    assert upload.status_code == 200
    return base


def test_describe_endpoint_requires_api_key(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(prompt: str, api_key: str) -> str:
        raise AssertionError("Gemini was called")

    monkeypatch.setattr("legacylift.cobol.describe.complete", fail)
    base = _upload_bank(client)
    response = client.post(f"{base}/describe")
    assert response.status_code == 400
    assert "LEGACYLIFT_GEMINI_API_KEY" in response.json()["detail"]


def test_describe_endpoint_returns_mocked_map(
    client_with_key: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("legacylift.cobol.describe.complete", lambda prompt, api_key: FAKE_MAP)
    base = _upload_bank(client_with_key)
    body = client_with_key.post(f"{base}/describe").json()
    assert body["programs"][0]["summary"] == "Nightly batch."
    assert body["shared_data"] == "They share ACCTDEF."

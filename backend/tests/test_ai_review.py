"""AI review: the prompt, a mocked Gemini call, and the project route."""

import json
import urllib.error
import urllib.request
from unittest.mock import patch

from legacylift.cobol.ai_review import (
    GEMINI_MODEL,
    ProgramFindings,
    build_prompt,
    request_gemini_review,
)
from legacylift.errors import AIReviewError
from legacylift.models import LineFinding

from helpers import HELLO, make_client


def test_prompt_includes_cobol_python_and_review_notes():
    prompt = build_prompt("DISPLAY 1.", "print(1)\n", ["Line 1: DISPLAY 1"])
    assert "1|DISPLAY 1." in prompt
    assert "1|print(1)" in prompt
    assert "- Line 1: DISPLAY 1" in prompt
    assert "Review notes:" in prompt


def test_request_parses_mocked_gemini_json():
    review = {
        "matches": [{"cobol_lines": [9], "python_lines": [4], "detail": "DISPLAY prints."}],
        "concerns": [
            {"cobol_lines": [11], "python_lines": [], "detail": "PERFORM was not proven."}
        ],
    }
    body = json.dumps({"candidates": [{"content": {"parts": [{"text": json.dumps(review)}]}}]})

    class FakeResponse:
        def read(self):
            return body.encode()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def fake_urlopen(request, timeout):
        assert request.full_url.endswith(f"{GEMINI_MODEL}:generateContent")
        assert "secret-key" not in request.full_url
        assert request.get_header("X-goog-api-key") == "secret-key"
        sent = json.loads(request.data.decode())
        assert "COBOL" in sent["contents"][0]["parts"][0]["text"]
        assert timeout == 5
        return FakeResponse()

    with patch.object(urllib.request, "urlopen", fake_urlopen):
        parsed = request_gemini_review("COBOL:\n1|DISPLAY 1.", api_key="secret-key", timeout=5)

    assert parsed.matches[0].cobol_lines == [9]
    assert parsed.concerns[0].python_lines == []
    assert parsed.concerns[0].detail == "PERFORM was not proven."


def test_request_turns_a_timeout_into_an_api_error():
    def fake_urlopen(request, timeout):
        raise TimeoutError

    with patch.object(urllib.request, "urlopen", fake_urlopen):
        try:
            request_gemini_review("prompt", api_key="secret-key", timeout=1)
        except AIReviewError as error:
            assert error.status_code == 502
            assert str(error) == "The AI review timed out."
        else:
            raise AssertionError("expected AIReviewError")


def test_request_rejects_a_non_json_review():
    body = json.dumps({"candidates": [{"content": {"parts": [{"text": "not json"}]}}]})

    class FakeResponse:
        def read(self):
            return body.encode()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    with patch.object(urllib.request, "urlopen", lambda *args, **kwargs: FakeResponse()):
        try:
            request_gemini_review("prompt", api_key="secret-key", timeout=1)
        except AIReviewError as error:
            assert "expected JSON" in str(error)
        else:
            raise AssertionError("expected AIReviewError")


def test_sample_program_route_returns_matches_concerns_and_lines(tmp_path, monkeypatch):
    client = make_client(tmp_path, gemini_api_key="test-key", gemini_timeout_seconds=5)
    demo = client.post("/api/projects/demo").json()
    project = f"/api/projects/{demo['id']}"
    assert client.post(f"{project}/convert").status_code == 200

    def fake(prompt, *, api_key, timeout):
        assert "PROGRAM-ID." in prompt
        assert "Review notes:" in prompt
        assert "Python:" in prompt
        assert api_key == "test-key"
        assert timeout == 5
        return ProgramFindings(
            matches=[
                LineFinding(cobol_lines=[28], python_lines=[12], detail="DISPLAY maps to print.")
            ],
            concerns=[
                LineFinding(cobol_lines=[36], python_lines=[20], detail="Check the amount due.")
            ],
        )

    monkeypatch.setattr("legacylift.services.projects.request_gemini_review", fake)
    response = client.post(f"{project}/ai-review")
    assert response.status_code == 200
    body = response.json()
    assert body["model"] == GEMINI_MODEL
    assert body["status"] == "concerns"
    assert "test-key" not in response.text
    file_review = body["files"][0]
    assert (file_review["source_name"], file_review["python_name"]) == (
        "BANKMAIN.cbl",
        "BANKMAIN.py",
    )
    assert file_review["matches"] == [
        {"cobol_lines": [28], "python_lines": [12], "detail": "DISPLAY maps to print."}
    ]
    assert file_review["concerns"] == [
        {"cobol_lines": [36], "python_lines": [20], "detail": "Check the amount due."}
    ]
    saved = client.get(f"{project}/runs/{body['run_id']}").json()
    assert saved["kind"] == "ai_review"
    assert saved["reviews"] == body["files"]


def test_clear_review_when_the_model_reports_no_concerns(tmp_path, monkeypatch):
    client = make_client(tmp_path, gemini_api_key="test-key")
    created = client.post("/api/projects", json={"name": "Hello"}).json()
    project = f"/api/projects/{created['id']}"
    client.post(f"{project}/files", files=[("files", ("hello.cbl", HELLO))])
    client.post(f"{project}/convert")
    monkeypatch.setattr(
        "legacylift.services.projects.request_gemini_review",
        lambda *args, **kwargs: ProgramFindings(
            matches=[LineFinding(cobol_lines=[9], python_lines=[3], detail="DISPLAY prints.")],
            concerns=[],
        ),
    )
    assert client.post(f"{project}/ai-review").json()["status"] == "clear"


def test_missing_api_key_does_not_call_the_model(tmp_path, monkeypatch):
    client = make_client(tmp_path)
    created = client.post("/api/projects", json={"name": "Hello"}).json()
    project = f"/api/projects/{created['id']}"
    client.post(f"{project}/files", files=[("files", ("hello.cbl", HELLO))])
    client.post(f"{project}/convert")

    def fail(*args, **kwargs):
        raise AssertionError("the model must not be called without an API key")

    monkeypatch.setattr("legacylift.services.projects.request_gemini_review", fail)
    response = client.post(f"{project}/ai-review")
    assert (response.status_code, response.json()["detail"]) == (
        400,
        "Set LEGACYLIFT_GEMINI_API_KEY before requesting an AI review.",
    )


def test_gemini_http_error_is_502(tmp_path, monkeypatch):
    client = make_client(tmp_path, gemini_api_key="test-key")
    created = client.post("/api/projects", json={"name": "Hello"}).json()
    project = f"/api/projects/{created['id']}"
    client.post(f"{project}/files", files=[("files", ("hello.cbl", HELLO))])
    client.post(f"{project}/convert")

    def fake_urlopen(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 400, "bad", hdrs=None, fp=None)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    response = client.post(f"{project}/ai-review")
    assert (response.status_code, response.json()["detail"]) == (
        502,
        "Gemini rejected the AI review request.",
    )

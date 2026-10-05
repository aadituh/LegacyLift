"""The project routes, in the order a user calls them, plus their errors."""

from unittest.mock import patch

import pytest

from helpers import HELLO, run_python

PAGES = "https://aadituh.github.io"


@pytest.fixture
def base(client) -> str:
    """URL of a new, empty project. It is the app's first, so its ID is "1"."""
    response = client.post("/api/projects", json={"name": "  Demo  "})
    assert response.status_code == 201
    return f"/api/projects/{response.json()['id']}"


def upload(client, base, *files):
    """POST (name, text) pairs to the project's files route."""
    return client.post(f"{base}/files", files=[("files", file) for file in files])


def test_full_project_flow(client, base):
    assert base == "/api/projects/1"
    assert client.get(base).json()["name"] == "Demo"

    # Upload three kinds of file plus a mistake, then remove the mistake.
    files = [("hello.cbl", HELLO), ("A.cpy", "01 A PIC X."), ("a.dat", "1"), ("oops.dat", "x")]
    added = upload(client, base, *files).json()["files"]
    assert [(f["id"], f["kind"]) for f in added][::3] == [("1", "program"), ("4", "data")]
    assert client.delete(f"{base}/files/4").status_code == 204
    assert [f["name"] for f in client.get(base).json()["files"]] == ["hello.cbl", "A.cpy", "a.dat"]

    # Analyze, convert, verify: runs "1", "2", "3".
    counts = client.post(f"{base}/analyze").json()
    assert counts["program_count"] == counts["copybook_count"] == counts["data_file_count"] == 1
    conversion = client.post(f"{base}/convert").json()
    assert (conversion["run_id"], conversion["status"]) == ("2", "draft")
    assert run_python(conversion["files"][0]["python"]) == "Hello, LegacyLift\nDemo count: 2\n"
    # Without GnuCOBOL: not_verified. With working cobc + matching stdout: verified.
    with patch("legacylift.cobol.equivalence.cobc_available", return_value=False):
        verify = client.post(f"{base}/verify").json()
    assert verify["status"] == "not_verified"
    assert verify["passed"] is None
    assert verify["files"]

    # Reopen: the run list is small; one run carries its Python.
    runs = client.get(f"{base}/runs").json()["runs"]
    assert [run["kind"] for run in runs] == ["analyze", "convert", "verify"]
    assert "files" not in runs[1]
    assert client.get(f"{base}/runs/2").json()["files"] == conversion["files"]
    downloaded = client.get(f"{base}/runs/2/files/hello.py")
    assert downloaded.status_code == 200
    assert downloaded.headers["content-type"].startswith("text/x-python")
    assert downloaded.headers["content-disposition"] == 'attachment; filename="hello.py"'
    assert downloaded.text == conversion["files"][0]["python"]
    missing = client.get(f"{base}/runs/2/files/missing.py")
    assert (missing.status_code, missing.json()) == (404, {"detail": "Python file not found."})

    # The project list: counts and last run, no file contents.
    [summary] = client.get("/api/projects").json()["projects"]
    assert (summary["program_count"], summary["last_run"]["kind"]) == (1, "verify")
    assert "files" not in summary and "files" not in summary["last_run"]

    response = client.delete(base)
    assert (response.status_code, response.content) == (204, b"")
    assert client.get("/api/projects").json() == {"projects": []}


def test_a_non_convert_run_has_no_python_file(client, base):
    upload(client, base, ("hello.cbl", HELLO))
    run_id = client.post(f"{base}/analyze").json()["run_id"]
    response = client.get(f"{base}/runs/{run_id}/files/hello.py")
    assert (response.status_code, response.json()) == (
        404,
        {"detail": "That run has no generated Python."},
    )


def test_demo_project_converts_with_no_review_notes(client):
    demo = client.post("/api/projects/demo").json()
    assert [file["id"] for file in demo["files"]] == ["1", "2", "3"]
    result = client.post(f"/api/projects/{demo['id']}/convert").json()
    assert result["status"] == "draft"
    assert "Amount due: $14" in run_python(result["files"][0]["python"])


def test_projects_are_listed_newest_first(client):
    assert client.get("/api/projects").json() == {"projects": []}
    for name in ("Old", "New"):
        client.post("/api/projects", json={"name": name})
    projects = client.get("/api/projects").json()["projects"]
    assert [(p["id"], p["name"], p["last_run"]) for p in projects] == [
        ("2", "New", None),
        ("1", "Old", None),
    ]


def test_failed_upload_adds_nothing_and_notes_mean_review(client, base):
    assert upload(client, base, ("hello.cbl", HELLO), ("x.txt", "x")).status_code == 400
    assert client.get(base).json()["files"] == []

    source = HELLO.replace("STOP RUN.", "PERFORM OTHER-STEP.\nSTOP RUN.")
    assert upload(client, base, ("review.cbl", source)).json()["files"][0]["id"] == "1"
    result = client.post(f"{base}/convert").json()
    assert result["status"] == result["files"][0]["status"] == "review_required"
    assert result["files"][0]["notes"] == ["Line 11: PERFORM OTHER-STEP"]


@pytest.mark.parametrize(
    ("files", "detail"),
    [
        ([("notes.txt", "x")], "notes.txt must be .cbl, .cob, .cpy, or .dat."),
        ([("REVIEW.CBL", HELLO)], "REVIEW.CBL is already in this project."),
        ([("review.cob", HELLO)], "COBOL program names must produce unique Python file names."),
        ([(f"d{n}.dat", "1") for n in range(10)], "A project needs 1 to 10 files."),
        ([("a" * 252 + ".dat", "1")], "File names must be at most 255 printable characters."),
    ],
)
def test_bad_upload_is_rejected(client, base, files, detail):
    upload(client, base, ("review.cbl", HELLO))  # already in the project
    response = upload(client, base, *files)
    assert (response.status_code, response.json()) == (400, {"detail": detail})


@pytest.mark.parametrize(
    ("method", "path", "status", "detail"),
    [
        ("GET", "/9", 404, "Project not found."),
        ("DELETE", "/9", 404, "Project not found."),
        ("POST", "/1/analyze", 400, "Upload files before analyzing."),
        ("POST", "/1/convert", 400, "Upload a .cbl or .cob program before converting."),
        ("POST", "/1/verify", 400, "Convert the project before requesting verification."),
        ("GET", "/1/runs/9", 404, "Run not found."),
        ("GET", "/1/runs/9/files/hello.py", 404, "Run not found."),
        ("DELETE", "/1/files/9", 404, "File not found."),
    ],
)
def test_errors_are_json_with_the_right_status(client, base, method, path, status, detail):
    response = client.request(method, f"/api/projects{path}")
    assert (response.status_code, response.json()) == (status, {"detail": detail})


def test_blank_name_is_rejected_and_the_browser_can_read_why(client):
    response = client.post("/api/projects", json={"name": "  "}, headers={"Origin": PAGES})
    assert response.json() == {"detail": "Project name cannot be blank."}
    assert (response.status_code, response.headers["access-control-allow-origin"]) == (400, PAGES)


@pytest.mark.parametrize("method", ["POST", "DELETE"])
def test_pages_origin_can_call_the_api(client, method):
    headers = {"Origin": PAGES, "Access-Control-Request-Method": method}
    preflight = client.options("/api/projects/1", headers=headers)
    assert (preflight.status_code, preflight.headers["access-control-allow-origin"]) == (200, PAGES)


def test_welcome_health_and_oversized_request(client):
    assert client.get("/").json()["docs"] == "/docs"
    assert client.get("/health").json() == {"status": "ok"}
    big = {"files": ("big.cbl", "x" * 1_300_000)}
    response = client.post("/api/convert", files=big, headers={"Origin": PAGES})
    assert (response.status_code, response.headers["access-control-allow-origin"]) == (413, PAGES)

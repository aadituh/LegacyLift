"""The project-based API workflow."""

import pytest

from helpers import make_client, run_python

HELLO = """IDENTIFICATION DIVISION.
PROGRAM-ID. HELLO-TEAM.
DATA DIVISION.
WORKING-STORAGE SECTION.
01 WS-NAME PIC X(20) VALUE "LegacyLift".
PROCEDURE DIVISION.
DISPLAY "Hello, " WS-NAME.
STOP RUN.
"""


@pytest.fixture
def base(client) -> str:
    """URL of a new, empty project."""
    response = client.post("/api/projects", json={"name": "  Demo  "})
    assert response.status_code == 201
    return f"/api/projects/{response.json()['id']}"


def test_create_upload_read_and_convert(client, base):
    upload = client.post(
        f"{base}/files",
        files=[
            ("files", ("hello.cbl", HELLO)),
            ("files", ("ACCTDEF.cpy", "01 ACCOUNT-RECORD PIC X(10).")),
            ("files", ("accounts.dat", "account 1")),
        ],
    )
    assert upload.status_code == 200
    assert [file["kind"] for file in upload.json()["files"]] == ["program", "copybook", "data"]

    project = client.get(base).json()
    assert project["name"] == "Demo"
    assert len(project["files"]) == 3
    assert project["files"][0]["content"] == HELLO

    conversion = client.post(f"{base}/convert")
    assert conversion.status_code == 200
    result = conversion.json()
    assert result["status"] == "draft"
    assert [file["python_name"] for file in result["files"]] == ["hello.py"]
    assert "print('Hello, '" in result["files"][0]["python"]
    runs = client.get(f"{base}/runs").json()["runs"]
    assert len(runs) == 1
    assert runs[0]["id"] == result["run_id"]
    assert (runs[0]["kind"], runs[0]["status"]) == ("convert", "draft")
    assert "created_at" in runs[0]
    assert "files" not in runs[0]  # the list stays small; fetch one run for its Python


def test_saved_conversion_can_be_fetched_again(client, base):
    client.post(f"{base}/files", files={"files": ("hello.cbl", HELLO)})
    conversion = client.post(f"{base}/convert").json()

    run = client.get(f"{base}/runs/{conversion['run_id']}")
    assert run.status_code == 200
    assert run.json()["kind"] == "convert"
    assert run.json()["files"] == conversion["files"]
    assert client.get(f"{base}/runs/missing").json() == {"detail": "Run not found."}


def test_upload_validation_is_atomic_and_review_status_is_explicit(client, base):
    bad = client.post(
        f"{base}/files",
        files=[
            ("files", ("hello.cbl", HELLO)),
            ("files", ("notes.txt", "not COBOL")),
        ],
    )
    assert bad.status_code == 400
    assert client.get(base).json()["files"] == []
    assert client.post(f"{base}/convert").status_code == 400

    review_source = HELLO.replace("STOP RUN.", "PERFORM OTHER-STEP.\nSTOP RUN.")
    good = client.post(f"{base}/files", files={"files": ("review.cbl", review_source)})
    assert good.status_code == 200
    result = client.post(f"{base}/convert").json()
    assert result["status"] == "review_required"
    assert result["files"][0]["status"] == "review_required"
    assert len(result["files"][0]["notes"]) == 1


@pytest.mark.parametrize(
    ("name", "detail"),
    [
        ("REVIEW.CBL", "REVIEW.CBL is already in this project."),
        ("review.cob", "COBOL program names must produce unique Python file names."),
    ],
)
def test_duplicate_names_are_rejected(client, base, name, detail):
    assert client.post(f"{base}/files", files={"files": ("review.cbl", HELLO)}).status_code == 200
    response = client.post(f"{base}/files", files={"files": (name, HELLO)})
    assert response.status_code == 400
    assert response.json() == {"detail": detail}


def test_project_file_limit(client, base):
    files = [("files", (f"data{n}.dat", "1")) for n in range(11)]
    response = client.post(f"{base}/files", files=files)
    assert response.json() == {"detail": "A project needs 1 to 10 files."}


def test_blank_project_name_is_rejected(client):
    response = client.post("/api/projects", json={"name": "   "})
    assert response.status_code == 400
    assert response.json() == {"detail": "Project name cannot be blank."}


def test_demo_project_exercises_all_project_routes(client, base):
    demo = client.post("/api/projects/demo")
    assert demo.status_code == 201
    project = demo.json()
    assert f"/api/projects/{project['id']}" != base
    assert [file["kind"] for file in project["files"]] == ["program", "copybook", "data"]
    demo_base = f"/api/projects/{project['id']}"

    analysis = client.post(f"{demo_base}/analyze")
    assert analysis.status_code == 200
    assert analysis.json()["status"] == "inventory_only"
    assert analysis.json()["program_count"] == 1
    assert analysis.json()["copybook_count"] == 1
    assert analysis.json()["data_file_count"] == 1

    conversion = client.post(f"{demo_base}/convert")
    assert conversion.status_code == 200
    assert conversion.json()["status"] == "draft"
    generated = conversion.json()["files"][0]
    assert generated["python_name"] == "store_report.py"
    assert "Amount due: $14" in run_python(generated["python"])

    verification = client.post(f"{demo_base}/verify")
    assert verification.status_code == 200
    assert verification.json()["status"] == "not_verified"
    assert verification.json()["passed"] is None

    runs = client.get(f"{demo_base}/runs").json()["runs"]
    assert [run["kind"] for run in runs] == ["analyze", "convert", "verify"]


def test_routes_require_the_right_project_state(client, base):
    assert client.get("/api/projects/missing").status_code == 404
    assert client.post("/api/projects/missing/convert").status_code == 404
    assert make_client(data_dir=None).get(base).status_code == 404  # another app
    assert client.post(f"{base}/analyze").status_code == 400
    assert client.post(f"{base}/verify").status_code == 400
    assert client.get(f"{base}/runs").json()["runs"] == []


def test_welcome_and_health_routes(client):
    assert client.get("/").json()["docs"] == "/docs"
    assert client.get("/health").json() == {"status": "ok"}


def test_pages_origin_can_call_the_api(client):
    origin = "https://aadituh.github.io"
    preflight = client.options(
        "/api/projects/demo",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
        },
    )
    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == origin

    # Error responses need the header too, or the browser hides the message.
    error = client.post("/api/projects", json={"name": " "}, headers={"Origin": origin})
    assert error.status_code == 400
    assert error.headers["access-control-allow-origin"] == origin


def test_oversized_request_is_refused_before_it_is_read(client):
    origin = "https://aadituh.github.io"
    big = "x" * 1_300_000
    response = client.post(
        "/api/convert", files={"files": ("big.cbl", big)}, headers={"Origin": origin}
    )
    assert response.status_code == 413
    assert response.headers["access-control-allow-origin"] == origin

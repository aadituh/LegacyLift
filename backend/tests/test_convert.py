"""The stateless upload-to-Python route used by the React demo."""

import pytest

from helpers import HELLO, run_python


def test_download_returns_the_generated_file(client):
    created = client.post("/api/convert", files={"files": ("hello.cbl", HELLO)})
    body = created.json()
    downloaded = client.get(f"/api/convert/{body['download_id']}/files/hello.py")
    assert downloaded.status_code == 200
    assert downloaded.headers["content-disposition"] == 'attachment; filename="hello.py"'
    assert downloaded.text == body["files"][0]["python"]
    missing = client.get(f"/api/convert/{body['download_id']}/files/other.py")
    assert (missing.status_code, missing.json()) == (404, {"detail": "Python file not found."})
    gone = client.get("/api/convert/missing-id/files/hello.py")
    assert gone.status_code == 404
    assert gone.json()["detail"] == "Download not found. Convert the files again."


def test_two_files_return_runnable_python(client):
    response = client.post(
        "/api/convert",
        files=[
            ("files", ("hello.cbl", HELLO)),
            ("files", ("second.cob", HELLO)),
        ],
    )
    assert response.status_code == 200
    files = response.json()["files"]
    assert [file["python_name"] for file in files] == ["hello.py", "second.py"]
    assert files[0]["notes"] == []
    assert run_python(files[0]["python"]) == "Hello, LegacyLift\nDemo count: 2\n"


def test_unsupported_line_is_marked_for_review(client):
    source = HELLO.replace("ADD 1 TO WS-COUNT.", "PERFORM OTHER-STEP.")
    response = client.post("/api/convert", files={"files": ("review.cbl", source)})
    assert response.status_code == 200
    result = response.json()["files"][0]
    assert "# TODO: COBOL line" in result["python"]
    assert len(result["notes"]) == 1


def test_folder_path_is_removed_from_file_name(client):
    response = client.post("/api/convert", files={"files": ("dir\\sub/hello.cbl", HELLO)})
    assert response.json()["files"][0]["source_name"] == "hello.cbl"


@pytest.mark.parametrize(
    ("files", "detail"),
    [
        ([("notes.txt", HELLO)], "notes.txt must be .cbl or .cob."),
        ([("bad.cbl", "DISPLAY HELLO.")], "bad.cbl: File needs PROGRAM-ID and PROCEDURE DIVISION."),
        ([("a.cbl", HELLO), ("A.cob", HELLO)], "COBOL file names must be unique."),
        ([(f"{n}.cbl", HELLO) for n in range(6)], "Choose 1 to 5 COBOL files."),
        ([("big.cbl", "x" * 100_001)], "big.cbl is larger than 100 KB."),
        ([("latin.cbl", "é".encode("latin-1"))], "latin.cbl must be UTF-8 text."),
        ([("binary.cbl", "PROGRAM-ID. X.\x00")], "binary.cbl is empty or binary."),
        ([("blank.cbl", "   ")], "blank.cbl is empty or binary."),
    ],
)
def test_bad_upload_is_rejected(client, files, detail):
    response = client.post("/api/convert", files=[("files", file) for file in files])
    assert response.status_code == 400
    assert response.json() == {"detail": detail}

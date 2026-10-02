"""Projects and their translations are saved as JSON and survive a restart."""

import json

from helpers import HELLO, make_client


def test_project_and_translation_survive_a_restart(tmp_path):
    first_app = make_client(tmp_path)
    project_id = first_app.post("/api/projects", json={"name": "Payroll"}).json()["id"]
    first_app.post(f"/api/projects/{project_id}/files", files={"files": ("hello.cbl", HELLO)})
    conversion = first_app.post(f"/api/projects/{project_id}/convert").json()
    assert (tmp_path / f"{project_id}.json").is_file()

    restarted = make_client(tmp_path)  # a new app reading the same folder
    project = restarted.get(f"/api/projects/{project_id}").json()
    assert project["name"] == "Payroll"
    assert [file["name"] for file in project["files"]] == ["hello.cbl"]
    run = restarted.get(f"/api/projects/{project_id}/runs/{conversion['run_id']}").json()
    assert run["files"] == conversion["files"]


def test_oldest_project_is_deleted_past_the_limit(tmp_path):
    client = make_client(tmp_path, max_projects=2)
    ids = [client.post("/api/projects", json={"name": f"P{n}"}).json()["id"] for n in range(3)]

    assert client.get(f"/api/projects/{ids[0]}").status_code == 404
    assert not (tmp_path / f"{ids[0]}.json").exists()
    assert sorted(path.stem for path in tmp_path.glob("*.json")) == sorted(ids[1:])


def test_unreadable_project_file_is_skipped(tmp_path):
    (tmp_path / "broken.json").write_text("{not json", encoding="utf-8")
    good = make_client(tmp_path).post("/api/projects", json={"name": "Good"}).json()

    restarted = make_client(tmp_path)
    assert restarted.get(f"/api/projects/{good['id']}").status_code == 200


def test_saved_file_is_plain_json(tmp_path):
    client = make_client(tmp_path)
    project_id = client.post("/api/projects/demo").json()["id"]
    saved = json.loads((tmp_path / f"{project_id}.json").read_text(encoding="utf-8"))
    assert saved["name"] == "LegacyLift demo"
    assert [file["kind"] for file in saved["files"]] == ["program", "copybook", "data"]

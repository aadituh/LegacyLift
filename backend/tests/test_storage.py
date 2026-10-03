"""Projects are saved as JSON files, survive a restart, and stay deleted."""

import json

from legacylift.models import Project
from legacylift.storage import ProjectStore

from helpers import HELLO, make_client


def test_projects_and_runs_survive_a_restart(tmp_path):
    first = make_client(tmp_path)
    first.post("/api/projects", json={"name": "Payroll"})
    first.post("/api/projects/1/files", files={"files": ("hello.cbl", HELLO)})
    conversion = first.post("/api/projects/1/convert").json()
    assert json.loads((tmp_path / "1.json").read_text(encoding="utf-8"))["name"] == "Payroll"

    restarted = make_client(tmp_path)  # a new app reading the same folder
    assert [f["name"] for f in restarted.get("/api/projects/1").json()["files"]] == ["hello.cbl"]
    assert restarted.get("/api/projects/1/runs/1").json()["files"] == conversion["files"]
    assert restarted.post("/api/projects", json={"name": "Next"}).json()["id"] == "2"


def test_oldest_project_is_deleted_past_the_limit(tmp_path):
    client = make_client(tmp_path, max_projects=2)
    for name in ("A", "B", "C"):
        client.post("/api/projects", json={"name": name})
    assert client.get("/api/projects/1").status_code == 404
    assert sorted(path.name for path in tmp_path.glob("*.json")) == ["2.json", "3.json"]


def test_deleted_project_stays_deleted(tmp_path):
    client = make_client(tmp_path)
    client.post("/api/projects/demo")
    client.delete("/api/projects/1")
    assert not (tmp_path / "1.json").exists()
    restarted = make_client(tmp_path)
    assert restarted.get("/api/projects/1").status_code == 404
    assert restarted.post("/api/projects", json={"name": "B"}).json()["id"] == "2"  # "1" not reused

    # A request that finishes after the delete must not write the file back.
    store = ProjectStore(tmp_path, max_projects=10)
    project = Project(id=store.next_id(), name="A")
    store.add(project)
    store.delete(project.id)
    store.save(project)
    assert not (tmp_path / f"{project.id}.json").exists()


def test_unreadable_and_old_style_files_do_not_break_startup(tmp_path):
    (tmp_path / "broken.json").write_text("{not json", encoding="utf-8")
    old = Project(id="5953abaa-ea30-4fd9-8352-2eb8487da3f7", name="Old")  # a UUID from before
    (tmp_path / f"{old.id}.json").write_text(old.model_dump_json(), encoding="utf-8")

    client = make_client(tmp_path)
    assert client.get(f"/api/projects/{old.id}").json()["name"] == "Old"
    assert client.post("/api/projects", json={"name": "New"}).json()["id"] == "1"

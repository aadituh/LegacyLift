"""Check the first project-based API workflow."""

import unittest

from fastapi.testclient import TestClient

from legacylift.main import create_app

SAMPLE = """IDENTIFICATION DIVISION.
PROGRAM-ID. HELLO-TEAM.
DATA DIVISION.
WORKING-STORAGE SECTION.
01 WS-NAME PIC X(20) VALUE "LegacyLift".
PROCEDURE DIVISION.
DISPLAY "Hello, " WS-NAME.
STOP RUN.
"""


class ProjectApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(create_app())
        response = self.client.post("/api/projects", json={"name": "  Demo  "})
        self.assertEqual(response.status_code, 201)
        self.project_id = response.json()["id"]
        self.base = f"/api/projects/{self.project_id}"

    def test_create_upload_read_and_convert(self):
        upload = self.client.post(f"{self.base}/files", files=[
            ("files", ("hello.cbl", SAMPLE)),
            ("files", ("ACCTDEF.cpy", "01 ACCOUNT-RECORD PIC X(10).")),
            ("files", ("accounts.dat", "account 1")),
        ])
        self.assertEqual(upload.status_code, 200)
        self.assertEqual([file["kind"] for file in upload.json()["files"]],
                         ["program", "copybook", "data"])

        project = self.client.get(self.base)
        self.assertEqual(project.json()["name"], "Demo")
        self.assertEqual(len(project.json()["files"]), 3)
        self.assertEqual(project.json()["files"][0]["content"], SAMPLE)

        conversion = self.client.post(f"{self.base}/convert")
        self.assertEqual(conversion.status_code, 200)
        result = conversion.json()
        self.assertEqual(result["status"], "draft")
        self.assertEqual(len(result["files"]), 1)
        self.assertEqual(result["files"][0]["python_name"], "hello.py")
        self.assertIn("print('Hello, '", result["files"][0]["python"])
        runs = self.client.get(f"{self.base}/runs").json()["runs"]
        self.assertEqual(runs, [{"id": result["run_id"], "kind": "convert", "status": "draft"}])

    def test_upload_validation_is_atomic_and_review_status_is_explicit(self):
        bad = self.client.post(f"{self.base}/files", files=[
            ("files", ("hello.cbl", SAMPLE)),
            ("files", ("notes.txt", "not COBOL")),
        ])
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(self.client.get(self.base).json()["files"], [])

        self.assertEqual(self.client.post(f"{self.base}/convert").status_code, 400)
        review_source = SAMPLE.replace("STOP RUN.", "PERFORM OTHER-STEP.\nSTOP RUN.")
        good = self.client.post(f"{self.base}/files", files={"files": ("review.cbl", review_source)})
        self.assertEqual(good.status_code, 200)
        duplicate = self.client.post(f"{self.base}/files", files={"files": ("REVIEW.CBL", SAMPLE)})
        self.assertEqual(duplicate.status_code, 400)
        result = self.client.post(f"{self.base}/convert").json()
        self.assertEqual(result["status"], "review_required")
        self.assertEqual(result["files"][0]["status"], "review_required")
        self.assertEqual(len(result["files"][0]["notes"]), 1)

    def test_demo_project_exercises_all_project_routes(self):
        demo = self.client.post("/api/projects/demo")
        self.assertEqual(demo.status_code, 201)
        project = demo.json()
        self.assertNotEqual(project["id"], self.project_id)
        self.assertEqual(
            [file["kind"] for file in project["files"]],
            ["program", "copybook", "data"],
        )
        demo_base = f"/api/projects/{project['id']}"

        analysis = self.client.post(f"{demo_base}/analyze")
        self.assertEqual(analysis.status_code, 200)
        self.assertEqual(analysis.json()["status"], "inventory_only")
        self.assertEqual(analysis.json()["program_count"], 1)
        self.assertEqual(analysis.json()["copybook_count"], 1)
        self.assertEqual(analysis.json()["data_file_count"], 1)

        conversion = self.client.post(f"{demo_base}/convert")
        self.assertEqual(conversion.status_code, 200)
        self.assertEqual(conversion.json()["status"], "draft")
        self.assertEqual(conversion.json()["files"][0]["python_name"], "hello_team.py")

        verification = self.client.post(f"{demo_base}/verify")
        self.assertEqual(verification.status_code, 200)
        self.assertEqual(verification.json()["status"], "not_verified")
        self.assertIsNone(verification.json()["passed"])

        runs = self.client.get(f"{demo_base}/runs").json()["runs"]
        self.assertEqual([run["kind"] for run in runs], ["analyze", "convert", "verify"])

    def test_routes_require_the_right_project_state(self):
        self.assertEqual(self.client.get("/api/projects/missing").status_code, 404)
        self.assertEqual(TestClient(create_app()).get(self.base).status_code, 404)
        self.assertEqual(self.client.post(f"{self.base}/analyze").status_code, 400)
        self.assertEqual(self.client.post(f"{self.base}/verify").status_code, 400)
        self.assertEqual(self.client.get(f"{self.base}/runs").json()["runs"], [])


if __name__ == "__main__":
    unittest.main()

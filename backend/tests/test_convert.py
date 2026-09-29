"""Check the upload-to-Python demo path."""

import contextlib
import io
import unittest

from fastapi.testclient import TestClient

from legacylift.main import create_app

SAMPLE = """IDENTIFICATION DIVISION.
PROGRAM-ID. HELLO-TEAM.
DATA DIVISION.
WORKING-STORAGE SECTION.
01 WS-NAME PIC X(20) VALUE "LegacyLift".
01 WS-COUNT PIC 9(3) VALUE 1.
PROCEDURE DIVISION.
DISPLAY "Hello, " WS-NAME.
ADD 1 TO WS-COUNT.
DISPLAY "Demo count: " WS-COUNT.
STOP RUN.
"""


class ConversionTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(create_app())

    def test_two_files_return_runnable_python(self):
        response = self.client.post("/api/convert", files=[
            ("files", ("hello.cbl", SAMPLE.encode("utf-8"))),
            ("files", ("second.cob", SAMPLE.encode("utf-8"))),
        ])
        self.assertEqual(response.status_code, 200)
        files = response.json()["files"]
        self.assertEqual([file["python_name"] for file in files], ["hello.py", "second.py"])
        self.assertEqual(files[0]["notes"], [])

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exec(files[0]["python"], {"__name__": "__main__"})
        self.assertEqual(output.getvalue(), "Hello, LegacyLift\nDemo count: 2\n")

    def test_unsupported_line_is_marked_for_review(self):
        source = SAMPLE.replace("ADD 1 TO WS-COUNT.", "PERFORM OTHER-STEP.")
        response = self.client.post("/api/convert", files={"files": ("review.cbl", source)})
        self.assertEqual(response.status_code, 200)
        result = response.json()["files"][0]
        self.assertIn("# TODO: COBOL line", result["python"])
        self.assertEqual(len(result["notes"]), 1)

    def test_bad_file_is_rejected(self):
        wrong_type = self.client.post("/api/convert", files={"files": ("notes.txt", SAMPLE)})
        self.assertEqual(wrong_type.status_code, 400)
        missing_program = self.client.post("/api/convert", files={"files": ("bad.cbl", "DISPLAY HELLO.")})
        self.assertEqual(missing_program.status_code, 400)


if __name__ == "__main__":
    unittest.main()

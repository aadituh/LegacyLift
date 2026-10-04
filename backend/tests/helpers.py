"""Shared test data and helpers."""

import contextlib
import io
from pathlib import Path

from fastapi.testclient import TestClient

from legacylift.config import Settings
from legacylift.main import create_app

HELLO = """IDENTIFICATION DIVISION.
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


def make_client(data_dir: Path | None, **settings: object) -> TestClient:
    """A client for a new app that ignores .env and saves projects to data_dir."""
    values: dict[str, object] = {"database_url": None, **settings}
    return TestClient(create_app(Settings(_env_file=None, data_dir=data_dir, **values)))


def run_python(code: str) -> str:
    """Run generated Python as a script and return what it printed."""
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        exec(code, {"__name__": "__main__"})  # noqa: S102 - running the output is the test
    return output.getvalue()

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from helpers import make_client


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    """A fresh app with an empty, temporary data folder."""
    return make_client(tmp_path)

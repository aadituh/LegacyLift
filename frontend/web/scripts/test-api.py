"""Isolated real FastAPI service used by browser tests; never reads .env."""
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend" / "src"))
import uvicorn
from legacylift.config import Settings
from legacylift.main import create_app
if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="legacylift-browser-") as directory:
        settings = Settings(_env_file=None, data_dir=Path(directory), database_url=None,
                            token_secret="isolated-browser-tests-only-at-least-32-characters", enable_runner=False,
                            gemini_api_key=None, require_login=True)
        uvicorn.run(create_app(settings), host="127.0.0.1", port=8011)


"""Serve a persistent, local-only review workspace without touching the project database."""
import os
import secrets
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(root / "backend" / "src"))
# The review instance always uses its own JSON store, including at import time.
os.environ["DATABASE_URL"] = ""
os.environ["LEGACYLIFT_DATABASE_URL"] = ""

import uvicorn
from legacylift.config import Settings
from legacylift.main import create_app

directory = root / "backend" / "data" / "web-review"
directory.mkdir(parents=True, exist_ok=True)
secret_path = directory / "token-secret.txt"
if not secret_path.exists():
    secret_path.write_text(secrets.token_urlsafe(48), encoding="utf-8")
settings = Settings(_env_file=[root / ".env", root / "backend" / ".env"]).model_copy(
    update={
        "database_url": None,
        "data_dir": directory,
        "token_secret": secret_path.read_text(encoding="utf-8").strip(),
        "require_login": True,
        "enable_runner": False,
        "neon_auth_url": "",
    }
)
app = create_app(settings)
store = app.state.project_service.store
email = "review@legacylift.local"
user = store.get_user_by_email(email)
if user is None:
    user = app.state.auth_service.register(email, "LegacyLiftReview1!", "Review Workspace")
if not app.state.project_service.list_projects(user.id):
    project = app.state.project_service.create_demo_project(owner_id=user.id)
    app.state.project_service.analyze(project)
print("Review API: http://127.0.0.1:8000; data: backend/data/web-review", flush=True)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)


"""Application entry point: FastAPI app wired to the prototype conversion pipeline."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse

PROTOTYPE_ROOT = Path(__file__).resolve().parents[2] / "prototype"
if str(PROTOTYPE_ROOT) not in sys.path:
    sys.path.insert(0, str(PROTOTYPE_ROOT))

from src.pipeline import analyze_source, convert_source  # noqa: E402

UI_PATH = Path(__file__).resolve().parents[3] / "frontend" / "index.html"
SAMPLE_COBOL = PROTOTYPE_ROOT / "data" / "simple_account.cbl"


def create_app() -> FastAPI:
    fastapi_app = FastAPI(title="LegacyLift")

    @fastapi_app.get("/", response_class=HTMLResponse)
    def demo_ui() -> str:
        if not UI_PATH.exists():
            raise HTTPException(status_code=500, detail="Demo UI is missing")
        return UI_PATH.read_text(encoding="utf-8")

    @fastapi_app.get("/health")
    def health() -> dict[str, str]:
        return {"message": "Hello from Legacy Lift."}

    @fastapi_app.get("/api/sample")
    def sample() -> dict[str, str]:
        if not SAMPLE_COBOL.exists():
            raise HTTPException(status_code=500, detail="Sample COBOL file missing")
        return {
            "name": SAMPLE_COBOL.name,
            "source": SAMPLE_COBOL.read_text(encoding="utf-8"),
        }

    @fastapi_app.post("/api/analyze")
    async def analyze(file: UploadFile = File(...)) -> dict:
        source = (await file.read()).decode("utf-8", errors="replace")
        if not source.strip():
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
        filename = file.filename or "upload.cbl"
        print(f"\n=== /api/analyze ← {filename} ===")
        return analyze_source(source, filename=filename)

    @fastapi_app.post("/api/convert")
    async def convert(file: UploadFile = File(...)) -> dict:
        source = (await file.read()).decode("utf-8", errors="replace")
        if not source.strip():
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
        filename = file.filename or "upload.cbl"
        print(f"\n=== /api/convert ← {filename} ===")
        return convert_source(source, filename=filename)

    return fastapi_app


app = create_app()

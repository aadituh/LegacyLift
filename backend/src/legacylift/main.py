"""Application entry point: builds the FastAPI app and wires routers."""

from __future__ import annotations

import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse

PROTOTYPE_ROOT = Path(__file__).resolve().parents[2] / "prototype"
if str(PROTOTYPE_ROOT) not in sys.path:
    sys.path.insert(0, str(PROTOTYPE_ROOT))
from src.cobol_parser import parse_cobol
from src.refactorer import OOPRefactorer
UI_PATH = Path(__file__).resolve().parent / "static" / "index.html"
SAMPLE_COBOL = PROTOTYPE_ROOT / "data" / "simple_account.cbl"



def create_app() -> FastAPI:
    fastapi_app = FastAPI(title="LegacyLift")
    @fastapi_app.get("/", response_class=HTMLResponse)
    def demo_ui() -> str:
        if not UI_PATH.exists():
            raise HTTPException(status_code=500, detail="Demo UI is missing")
        return UI_PATH.read_text(encoding="utf-8")
    @fastapi_app.get("/health")
    def hello() -> dict[str, str]:
        return {"message": "Hello from Legacy Lift."}
    @fastapi_app.get("/api/sample")
    def sample() -> dict[str, str]:
        return {
            "name": SAMPLE_COBOL.name,
            "source": SAMPLE_COBOL.read_text(encoding="utf-8"),
        }
    @fastapi_app.post("/api/analyze")
    async def analyze(file: UploadFile = File(...)) -> dict:
        source = (await file.read()).decode("utf-8", errors="replace")
        if not source.strip():
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
        with NamedTemporaryFile(mode="w", suffix=".cbl", delete=False, encoding="utf-8") as handle:
            handle.write(source)
            path = handle.name
        try:
            parsed = parse_cobol(path)
        finally:
            Path(path).unlink(missing_ok=True)
        return {
            "filename": file.filename,
            "program_name": parsed.get("program_name"),
            "attributes": parsed.get("potential_attributes"),
            "methods": parsed.get("potential_methods"),
            "paragraphs": [
                {"name": name, "body": body}
                for name, body in parsed.get("raw_paragraphs", [])
            ],
        }
    @fastapi_app.post("/api/convert")
    async def convert(file: UploadFile = File(...)) -> dict:
        source = (await file.read()).decode("utf-8", errors="replace")
        if not source.strip():
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
        with NamedTemporaryFile(mode="w", suffix=".cbl", delete=False, encoding="utf-8") as handle:
            handle.write(source)
            path = handle.name
        try:
            python_code = OOPRefactorer().refactor(path)
        finally:
            Path(path).unlink(missing_ok=True)
        return {"filename": file.filename, "python": python_code}
    return fastapi_app
app = create_app()
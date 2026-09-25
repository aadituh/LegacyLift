"""Application entry point: builds the FastAPI app and wires routers."""

from __future__ import annotations

import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

PROTOTYPE_ROOT = Path(__file__).resolve().parents[2] / "prototype"
if str(PROTOTYPE_ROOT) not in sys.path:
    sys.path.insert(0, str(PROTOTYPE_ROOT))
from src.cobol_parser import parse_cobol
UI_PATH = Path(__file__).resolve().parents[3] / "frontend" / "index.html"
SAMPLE_COBOL = PROTOTYPE_ROOT / "data" / "simple_account.cbl"



def create_app() -> FastAPI:
    fastapi_app = FastAPI(title="LegacyLift")
    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @fastapi_app.exception_handler(Exception)
    async def unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
        if isinstance(exc, HTTPException):
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
        return JSONResponse(status_code=500, content={"detail": str(exc)})

    @fastapi_app.get("/")
    def demo_ui() -> FileResponse:
        if not UI_PATH.exists():
            raise HTTPException(status_code=500, detail="Demo UI is missing")
        return FileResponse(UI_PATH, headers={"Cache-Control": "no-store"})
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
            from src.refactorer import OOPRefactorer
            python_code = OOPRefactorer().refactor(path)
        finally:
            Path(path).unlink(missing_ok=True)
        return {"filename": file.filename, "python": python_code}
    return fastapi_app
app = create_app()
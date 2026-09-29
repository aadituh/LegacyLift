"""One file-upload route for the LegacyLift teaching demo."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from legacylift.converter import convert_source

MAX_FILES = 5
MAX_FILE_BYTES = 100_000
logger = logging.getLogger("uvicorn.error")


def invalid_upload(message: str) -> HTTPException:
    """Use the same message in the server log and the API response."""
    logger.warning("Rejected upload: %s", message)
    return HTTPException(status_code=400, detail=message)


def create_app() -> FastAPI:
    app = FastAPI(title="LegacyLift API")
    origins = os.getenv(
        "LEGACYLIFT_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[origin.strip() for origin in origins.split(",") if origin.strip()],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.post("/api/convert")
    async def convert(files: list[UploadFile] = File(...)) -> dict:
        if not 1 <= len(files) <= MAX_FILES:
            raise invalid_upload("Choose 1 to 5 COBOL files.")

        results = []
        output_names = set()
        logger.info("Received %d COBOL file(s)", len(files))
        for file in files:
            # Browsers send a name, but it may contain path separators.
            name = Path((file.filename or "").replace("\\", "/")).name
            if Path(name).suffix.lower() not in {".cbl", ".cob"}:
                raise invalid_upload(f"{name or 'File'} must be .cbl or .cob.")

            output_name = f"{Path(name).stem}.py"
            if output_name.lower() in output_names:
                raise invalid_upload("COBOL file names must be unique.")
            output_names.add(output_name.lower())

            raw = await file.read(MAX_FILE_BYTES + 1)
            if len(raw) > MAX_FILE_BYTES:
                raise invalid_upload(f"{name} is larger than 100 KB.")
            try:
                source = raw.decode("utf-8-sig")
            except UnicodeDecodeError as error:
                raise invalid_upload(f"{name} must be UTF-8 text.") from error
            if not source.strip() or "\x00" in source:
                raise invalid_upload(f"{name} is empty or binary.")

            try:
                converted = convert_source(source)
            except ValueError as error:
                raise invalid_upload(f"{name}: {error}") from error
            results.append({"source_name": name, "python_name": output_name, **converted})
            logger.info("Converted %s with %d review notes", name, len(converted["notes"]))

        return {"files": results}

    return app


app = create_app()

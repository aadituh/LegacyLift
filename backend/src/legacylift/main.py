"""Builds the FastAPI app: the entry point of the backend.

``create_app`` sets up, in order: the request size limit (413), CORS for the
frontend, one error handler that turns any ``LegacyLiftError`` into
``{"detail": message}``, the ``ProjectStore`` and ``ProjectService`` (kept on
``app.state``), the two routers, and the ``/`` and ``/health`` routes.

Uvicorn imports the module-level ``app``:
``uv run --frozen uvicorn legacylift.main:app --reload``.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.body_limit import RequestBodyLimitMiddleware

from legacylift.config import Settings
from legacylift.errors import LegacyLiftError
from legacylift.neon_store import NeonProjectStore
from legacylift.routers import convert, projects
from legacylift.services.batch_downloads import BatchDownloadStore
from legacylift.services.projects import ProjectService
from legacylift.storage import ProjectRepository, ProjectStore

logger = logging.getLogger("uvicorn.error")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the app.

    Args:
        settings: Settings to use. ``None`` reads them from the environment.
            Tests pass their own, for example with a temporary ``data_dir``.

    Returns:
        The configured FastAPI app.

    Example:
        >>> from fastapi.testclient import TestClient
        >>> app = create_app(Settings(_env_file=None, data_dir=None, database_url=None))
        >>> TestClient(app).get("/health").json()
        {'status': 'ok'}
    """
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        """Close the database pool when the API stops."""
        yield
        closer = getattr(app.state.project_service.store, "close", None)
        if closer is not None:
            closer()

    app = FastAPI(title="LegacyLift API", lifespan=lifespan)

    # The middleware added last runs first. CORS goes last so that even a
    # "too large" (413) response has CORS headers and the browser can read it.
    app.add_middleware(RequestBodyLimitMiddleware, max_body_size=settings.max_request_bytes)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.all_cors_origins,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.exception_handler(LegacyLiftError)
    async def handle_legacylift_error(request: Request, error: LegacyLiftError) -> JSONResponse:
        """Send a service error as ``{"detail": message}`` with its status, and log it.

        Args:
            request: The request that failed.
            error: The error a service raised.

        Returns:
            A JSON response with ``error.status_code``.
        """
        logger.warning("Rejected %s %s: %s", request.method, request.url.path, error)
        return JSONResponse(status_code=error.status_code, content={"detail": str(error)})

    store: ProjectRepository
    if settings.database_url:
        logger.info("Storing projects in Neon Postgres")
        store = NeonProjectStore(settings.database_url, settings.max_projects)
    else:
        store = ProjectStore(settings.data_dir, settings.max_projects)
    app.state.project_service = ProjectService(store, cobc_path=settings.cobc_path)
    app.state.batch_downloads = BatchDownloadStore()
    app.include_router(projects.router)
    app.include_router(convert.router)

    @app.get("/")
    def home() -> dict[str, str]:
        """Point visitors to the health check and the interactive docs.

        Returns:
            A short message with the ``/health`` and ``/docs`` paths.
        """
        return {"message": "LegacyLift API is running", "health": "/health", "docs": "/docs"}

    @app.get("/health")
    def health() -> dict[str, str]:
        """Report that the API is up. The frontend calls this on page load.

        Returns:
            ``{"status": "ok"}``.
        """
        return {"status": "ok"}

    return app


app = create_app()

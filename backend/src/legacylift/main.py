"""FastAPI application setup."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from legacylift.routers import legacy, projects
from legacylift.repositories.projects import ProjectRepository
from legacylift.services.projects import ProjectService


def create_app() -> FastAPI:
    app = FastAPI(title="LegacyLift API")
    # Keep local Vite and the GitHub Pages frontend reachable by default.
    default_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://aadituh.github.io",
    ]
    extra_origins = os.getenv("LEGACYLIFT_CORS_ORIGINS", "")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=default_origins + [
            origin.strip() for origin in extra_origins.split(",") if origin.strip()
        ],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    # One repository per app keeps local projects and tests separate.
    app.state.project_service = ProjectService(ProjectRepository())
    app.include_router(projects.router)
    app.include_router(legacy.router)

    @app.get("/")
    def home() -> dict[str, str]:
        return {
            "message": "LegacyLift API is running",
            "health": "/health",
            "docs": "/docs",
        }

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()

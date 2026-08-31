"""Application entry point: builds the FastAPI app and wires routers."""

from fastapi import FastAPI


def create_app() -> FastAPI:
    """Create and configure the LegacyLift FastAPI application."""
    fastapi_app = FastAPI(title="LegacyLift")

    @fastapi_app.get("/")
    def hello() -> dict[str, str]:
        """Return a basic liveness greeting."""
        return {"message": "Hello from LegacyLift"}

    return fastapi_app


app = create_app()

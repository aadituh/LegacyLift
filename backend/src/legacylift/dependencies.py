"""Dependencies supplied to route functions by FastAPI."""

from typing import Annotated

from fastapi import Depends, Request

from legacylift.services.projects import ProjectService


def get_project_service(request: Request) -> ProjectService:
    return request.app.state.project_service


ProjectServiceDep = Annotated[ProjectService, Depends(get_project_service)]

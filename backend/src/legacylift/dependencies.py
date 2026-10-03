"""Values FastAPI passes into route functions (dependency injection).

A route parameter typed ``ProjectServiceDep`` receives the app's
``ProjectService``. One typed ``ProjectDep`` receives the project named by
``{project_id}`` in the URL, or the request stops with 404 before the route
runs.
"""

from typing import Annotated, cast

from fastapi import Depends, Request

from legacylift.models import Project
from legacylift.services.projects import ProjectService


def get_project_service(request: Request) -> ProjectService:
    """Return the service that ``create_app`` stored on the app.

    Args:
        request: The current request; FastAPI passes it in.

    Returns:
        The app's ``ProjectService``.
    """
    return cast(ProjectService, request.app.state.project_service)


ProjectServiceDep = Annotated[ProjectService, Depends(get_project_service)]


def get_project_from_url(project_id: str, service: ProjectServiceDep) -> Project:
    """Load the project named by ``{project_id}`` in the URL.

    Args:
        project_id: From the URL.
        service: Injected by FastAPI.

    Returns:
        The project.

    Raises:
        NotFoundError: If there is no such project (404).
    """
    return service.get_project(project_id)


ProjectDep = Annotated[Project, Depends(get_project_from_url)]

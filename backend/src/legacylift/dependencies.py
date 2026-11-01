"""Values FastAPI passes into route functions (dependency injection).

A route parameter typed ``ProjectServiceDep`` receives the app's
``ProjectService``. One typed ``ProjectDep`` receives the project named by
``{project_id}`` in the URL, or the request stops with 404 before the route
runs. ``BatchDownloadDep`` receives the in-memory batch conversions.
"""

from typing import Annotated, cast

from fastapi import Depends, Header, Request

from legacylift.config import Settings
from legacylift.errors import NotFoundError, UnauthenticatedError
from legacylift.models import Project, User
from legacylift.services.auth import AuthService
from legacylift.services.batch_downloads import BatchDownloadStore
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


def get_auth_service(request: Request) -> AuthService:
    """Return the auth service that ``create_app`` stored on the app.

    Args:
        request: The current request; FastAPI passes it in.

    Returns:
        The app's ``AuthService``.
    """
    return cast(AuthService, request.app.state.auth_service)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def _bearer_token(authorization: str | None) -> str | None:
    """Return the token from ``Authorization: Bearer <token>``, or ``None`` if absent.

    Raises:
        UnauthenticatedError: The header is present but not a bearer token.
    """
    if authorization is None or not authorization.strip():
        return None
    scheme, _, token = authorization.strip().partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise UnauthenticatedError("Invalid login token.")
    return token.strip()


def get_current_user(
    auth: AuthServiceDep,
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    """Return the account for ``Authorization: Bearer <token>``.

    Args:
        auth: The auth service.
        authorization: The raw header, or ``None`` when the client omitted it.

    Returns:
        The account.

    Raises:
        UnauthenticatedError: The token is missing, wrong, or expired (401).
    """
    token = _bearer_token(authorization)
    if token is None:
        raise UnauthenticatedError("Missing login token.")
    return auth.user_from_token(token)


CurrentUserDep = Annotated[User, Depends(get_current_user)]


def get_active_user(
    request: Request,
    auth: AuthServiceDep,
    authorization: Annotated[str | None, Header()] = None,
) -> User | None:
    """Return the logged-in account when login is required, otherwise ``None``.

    Project routes use this so they keep working until the login pages turn
    ``LEGACYLIFT_REQUIRE_LOGIN`` on.

    Args:
        request: The current request.
        auth: The auth service.
        authorization: The raw header.

    Returns:
        The account, or ``None`` when login is not required.

    Raises:
        UnauthenticatedError: Login is required and the token is missing or bad (401).
    """
    settings = cast(Settings, request.app.state.settings)
    if not settings.require_login:
        return None
    token = _bearer_token(authorization)
    if token is None:
        raise UnauthenticatedError("Missing login token.")
    return auth.user_from_token(token)


ActiveUserDep = Annotated[User | None, Depends(get_active_user)]


def get_batch_downloads(request: Request) -> BatchDownloadStore:
    """Return the in-memory store of batch conversions.

    Args:
        request: The current request; FastAPI passes it in.

    Returns:
        The app's ``BatchDownloadStore``.
    """
    return cast(BatchDownloadStore, request.app.state.batch_downloads)


BatchDownloadDep = Annotated[BatchDownloadStore, Depends(get_batch_downloads)]


def get_project_from_url(
    project_id: str,
    service: ProjectServiceDep,
    user: ActiveUserDep,
) -> Project:
    """Load the project named by ``{project_id}`` in the URL.

    When login is required, another account's project is the same 404 as a
    missing one.

    Args:
        project_id: From the URL.
        service: Injected by FastAPI.
        user: The logged-in account, or ``None`` when login is off.

    Returns:
        The project.

    Raises:
        NotFoundError: If there is no such project, or it belongs to someone else (404).
    """
    project = service.get_project(project_id)
    if user is not None and project.owner_id != user.id:
        raise NotFoundError("Project not found.")
    return project


ProjectDep = Annotated[Project, Depends(get_project_from_url)]

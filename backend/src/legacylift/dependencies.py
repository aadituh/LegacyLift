"""Values FastAPI passes into route functions (dependency injection).

A route parameter typed ``ProjectServiceDep`` receives the app's
``ProjectService``. One typed ``ProjectDep`` receives the project named by
``{project_id}`` in the URL, or the request stops with 404 before the route
runs. ``BatchDownloadDep`` receives the in-memory batch conversions.
"""

from dataclasses import dataclass
from typing import Annotated, cast

import jwt
from fastapi import Depends, Header, Request

from legacylift.config import Settings
from legacylift.errors import NotFoundError, UnauthenticatedError
from legacylift.models import Project
from legacylift.schemas import UserResponse
from legacylift.services.auth import AuthService
from legacylift.services.batch_downloads import BatchDownloadStore
from legacylift.services.neon_auth import NeonAuth
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


def get_account(
    request: Request,
    auth: AuthServiceDep,
    authorization: Annotated[str | None, Header()] = None,
) -> UserResponse:
    """Return the account for ``Authorization: Bearer <token>``.

    An API login token names an account in storage. A Neon Auth token (EdDSA)
    names a Neon account; its email and name come from the token.

    Args:
        request: The current request.
        auth: The auth service. Used for the API's own login tokens.
        authorization: The raw header, or ``None`` when the client omitted it.

    Returns:
        The account, without a password hash.

    Raises:
        UnauthenticatedError: The token is missing, wrong, or expired, or it is a
            Neon token and Neon Auth is not configured (401).
    """
    token = _bearer_token(authorization)
    if token is None:
        raise UnauthenticatedError("Missing login token.")
    if _jwt_algorithm(token) == "EdDSA":
        neon = cast(NeonAuth | None, getattr(request.app.state, "neon_auth", None))
        if neon is None:
            raise UnauthenticatedError("Invalid login token.")
        account = neon.account(token)
        return UserResponse(
            id=account.id,
            email=account.email,
            display_name=account.display_name,
            created_at=account.created_at,
        )
    user = auth.user_from_token(token)
    return UserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        created_at=user.created_at,
    )


AccountDep = Annotated[UserResponse, Depends(get_account)]


@dataclass(frozen=True, slots=True)
class SignedIn:
    """Account id from a verified bearer token.

    Attributes:
        id: Neon Auth user id, or the API account id when that token was used.
    """

    id: str


def _jwt_algorithm(token: str) -> str | None:
    """Return the unverified ``alg`` header, or ``None`` when the token is not a JWT."""
    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError:
        return None
    algorithm = header.get("alg")
    return algorithm if isinstance(algorithm, str) else None


def get_active_user(
    request: Request,
    auth: AuthServiceDep,
    authorization: Annotated[str | None, Header()] = None,
) -> SignedIn | None:
    """Return the account id for a Neon Auth token, or for an API token when login is required.

    A Neon Auth token (EdDSA) or an API login token sets the project owner
    even when ``LEGACYLIFT_REQUIRE_LOGIN`` is off. With no token, project
    routes stay open until that flag is turned on.

    Args:
        request: The current request.
        auth: The auth service. Used for the API's own login tokens.
        authorization: The raw header.

    Returns:
        The account id, or ``None`` when no token was sent and login is not required.

    Raises:
        UnauthenticatedError: The token is bad, or login is required and the
            token is missing or bad (401).
    """
    settings = cast(Settings, request.app.state.settings)
    token = _bearer_token(authorization)
    if token is None:
        if settings.require_login:
            raise UnauthenticatedError("Missing login token.")
        return None
    if _jwt_algorithm(token) == "EdDSA":
        neon = cast(NeonAuth | None, getattr(request.app.state, "neon_auth", None))
        if neon is None:
            raise UnauthenticatedError("Invalid login token.")
        return SignedIn(neon.user_id(token))
    return SignedIn(auth.user_from_token(token).id)


ActiveUserDep = Annotated[SignedIn | None, Depends(get_active_user)]


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

    A project with an owner is visible only to that account. Another account,
    or a request with no token, gets the same 404 as a missing project.

    Args:
        project_id: From the URL.
        service: Injected by FastAPI.
        user: The signed-in account, or ``None`` when the request had no token
            and login is not required.

    Returns:
        The project.

    Raises:
        NotFoundError: If there is no such project, or it belongs to someone else (404).
    """
    project = service.get_project(project_id)
    owner = user.id if user is not None else None
    if project.owner_id != owner:
        raise NotFoundError("Project not found.")
    return project


ProjectDep = Annotated[Project, Depends(get_project_from_url)]

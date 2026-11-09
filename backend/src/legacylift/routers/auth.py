"""Account routes under ``/api/auth``.

Register, log in, and read the current account. Passwords are not written to
the response or the log. Project routes use these tokens only when
``LEGACYLIFT_REQUIRE_LOGIN`` is on. A Neon Auth token is accepted on project
routes and on ``/me`` whenever the client sends one.
"""

from fastapi import APIRouter

from legacylift.dependencies import AccountDep, AuthServiceDep
from legacylift.models import User
from legacylift.schemas import LoginRequest, LoginResponse, RegisterRequest, UserResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _public_user(user: User) -> UserResponse:
    """Copy the account fields clients are allowed to see."""
    return UserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        created_at=user.created_at,
    )


@router.post("/register", response_model=UserResponse, status_code=201)
def register(body: RegisterRequest, auth: AuthServiceDep) -> UserResponse:
    """Create an account and return it without the password or its hash.

    \f
    Raises:
        InputError: The email, display name, or password is not acceptable (422).
        ConflictError: The email is already registered (409).
    """
    return _public_user(auth.register(body.email, body.password, body.display_name))


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, auth: AuthServiceDep) -> LoginResponse:
    """Return a signed token that expires.

    A wrong email and a wrong password return the same 401 message.

    \f
    Raises:
        ProjectStateError: ``LEGACYLIFT_TOKEN_SECRET`` is unset (400).
        UnauthenticatedError: The email or password is wrong (401).
    """
    token = auth.login(body.email, body.password)
    return LoginResponse(token=token, expires_in=auth.ttl_seconds)


@router.get("/me", response_model=UserResponse)
def me(account: AccountDep) -> UserResponse:
    """Return the account for a valid token.

    \f
    Accepts an API login token or a Neon Auth token.

    Raises:
        UnauthenticatedError: The token is missing, wrong, or expired (401).
    """
    return account

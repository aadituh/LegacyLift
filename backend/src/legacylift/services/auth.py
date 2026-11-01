"""Sign up, sign in, and read the account behind a login token.

Passwords are hashed with Argon2 and never logged or returned. Tokens are
HS256 JWTs signed with ``LEGACYLIFT_TOKEN_SECRET``. A wrong email and a wrong
password produce the same message.

Agreed with the login page (#15), sign-up page (#32), and accounts table (#30):

- Token lifetime defaults to 24 hours (``LEGACYLIFT_TOKEN_TTL_SECONDS``).
- The frontend keeps the token in ``localStorage`` under ``legacylift-token``
  and sends ``Authorization: Bearer <token>``.
- A password is 8 to 128 characters and includes a letter and a number.
- A display name is 1 to 100 characters: letters, numbers, spaces, periods,
  apostrophes, and hyphens.
- Project routes require this token only when ``LEGACYLIFT_REQUIRE_LOGIN`` is on.
  A Neon Auth token is accepted on those routes whenever the client sends one.
"""

import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import Protocol

import jwt
from pwdlib import PasswordHash

from legacylift.errors import InputError, ProjectStateError, UnauthenticatedError
from legacylift.models import User

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_DISPLAY_NAME = re.compile(r"[A-Za-z0-9 .'-]+")
PASSWORD_RULE = "Password must be 8 to 128 characters and include a letter and a number."
DISPLAY_NAME_RULE = (
    "Display name must be 1 to 100 characters and use only letters, numbers, "
    "spaces, periods, apostrophes, and hyphens."
)
INVALID_LOGIN = "Invalid email or password."
MISSING_SECRET = "Set LEGACYLIFT_TOKEN_SECRET before signing in."


class AccountStore(Protocol):
    """The account methods both project stores provide."""

    def add_user(self, user: User) -> None:
        """Save an account."""

    def get_user(self, user_id: str) -> User | None:
        """Find an account by ID."""

    def get_user_by_email(self, email: str) -> User | None:
        """Find an account by lowercase email."""


def normalize_email(email: str) -> str:
    """Strip an email and lowercase it.

    Args:
        email: The address as typed.

    Returns:
        The address to store and look up.

    Example:
        >>> normalize_email("  Ada@Example.com ")
        'ada@example.com'
    """
    return email.strip().lower()


def password_is_strong(password: str) -> bool:
    """Return whether a password meets the sign-up rule.

    Args:
        password: The password as typed. It is not stored.

    Returns:
        True when it is 8 to 128 characters and has a letter and a number.

    Example:
        >>> password_is_strong("correct horse 1")
        True
        >>> password_is_strong("short1")
        False
    """
    if not 8 <= len(password) <= 128:
        return False
    return any(character.isalpha() for character in password) and any(
        character.isdigit() for character in password
    )


class AuthService:
    """Create accounts, check passwords, and sign tokens."""

    def __init__(self, store: AccountStore, *, secret: str | None, ttl_seconds: int) -> None:
        """Create the service.

        Args:
            store: Where accounts are saved.
            secret: HMAC secret. Blank means tokens cannot be signed.
            ttl_seconds: How long a new token stays valid.
        """
        self.store = store
        self.secret = secret.strip() if secret and secret.strip() else None
        self.ttl_seconds = ttl_seconds
        self._hasher = PasswordHash.recommended()
        self._dummy_hash = self._hasher.hash("not-a-real-password")

    def register(self, email: str, password: str, display_name: str) -> User:
        """Save a new account and return it. The hash stays on the stored user.

        Args:
            email: Stored lowercase.
            password: Checked, then hashed. Not saved or logged.
            display_name: Shown in the header.

        Returns:
            The new account.

        Raises:
            InputError: The email, name, or password is not acceptable (422).
            ConflictError: The email is already registered (409).
        """
        normalized = normalize_email(email)
        if not _EMAIL.fullmatch(normalized) or len(normalized) > 254:
            raise InputError("Enter a valid email address.")
        name = display_name.strip()
        if not name or len(name) > 100 or _DISPLAY_NAME.fullmatch(name) is None:
            raise InputError(DISPLAY_NAME_RULE)
        if not password_is_strong(password):
            raise InputError(PASSWORD_RULE)
        user = User(
            id=str(uuid.uuid4()),
            email=normalized,
            password_hash=self._hasher.hash(password),
            display_name=name,
        )
        self.store.add_user(user)
        return user

    def login(self, email: str, password: str) -> str:
        """Return a signed token, or the same error for a bad email or password.

        Args:
            email: Compared after lowercasing.
            password: Checked against the hash. Not logged.

        Returns:
            A JWT that expires after ``ttl_seconds``.

        Raises:
            ProjectStateError: ``LEGACYLIFT_TOKEN_SECRET`` is unset (400).
            UnauthenticatedError: The email or password is wrong (401).
        """
        if self.secret is None:
            raise ProjectStateError(MISSING_SECRET)
        user = self.store.get_user_by_email(normalize_email(email))
        hashed = user.password_hash if user is not None else self._dummy_hash
        matches = self._matches(password, hashed)
        if user is None or not matches:
            raise UnauthenticatedError(INVALID_LOGIN)
        expires = datetime.now(UTC) + timedelta(seconds=self.ttl_seconds)
        token = jwt.encode({"sub": user.id, "exp": expires}, self.secret, algorithm="HS256")
        return token if isinstance(token, str) else token.decode()

    def user_from_token(self, token: str) -> User:
        """Return the account named by a token.

        Args:
            token: The JWT, without the ``Bearer`` prefix.

        Returns:
            The account.

        Raises:
            UnauthenticatedError: The token is wrong, expired, or names no account (401).
        """
        if self.secret is None:
            raise UnauthenticatedError("Invalid login token.")
        try:
            payload = jwt.decode(token, self.secret, algorithms=["HS256"])
        except jwt.ExpiredSignatureError as error:
            raise UnauthenticatedError("Please log in again.") from error
        except jwt.InvalidTokenError as error:
            raise UnauthenticatedError("Invalid login token.") from error
        user_id = payload.get("sub") if isinstance(payload, dict) else None
        user = self.store.get_user(user_id) if isinstance(user_id, str) else None
        if user is None:
            raise UnauthenticatedError("Invalid login token.")
        return user

    def _matches(self, password: str, password_hash: str) -> bool:
        """Return whether ``password`` matches ``password_hash``. Never raises."""
        try:
            return bool(self._hasher.verify(password, password_hash))
        except (ValueError, TypeError):
            return False

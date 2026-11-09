"""Verify a Neon Auth JWT and return the signed-in user.

The web app signs in with Neon Auth and sends ``Authorization: Bearer`` from
``authClient.token()``. That token is EdDSA, not the API's own HS256 login
token. The public keys come from ``{neon auth url}/.well-known/jwks.json``.
The issuer and audience are the origin of that URL (no path). The user id is
the ``sub`` claim, which matches ``neon_auth."user".id``.
"""

import threading
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol, cast
from urllib.error import URLError
from urllib.parse import urlparse

import jwt
from jwt.exceptions import PyJWKClientError

from legacylift.errors import UnauthenticatedError


@dataclass(frozen=True, slots=True)
class NeonAccount:
    """The account a verified Neon Auth token names.

    Attributes:
        id: Lowercase UUID from ``sub``.
        email: Lowercase email from the ``email`` claim, or ``""``.
        display_name: The ``name`` claim, else the part of the email before ``@``.
        created_at: The ``createdAt`` claim, else the token's issue time (UTC).
    """

    id: str
    email: str
    display_name: str
    created_at: datetime


class SigningKeys(Protocol):
    """The piece of ``PyJWKClient`` this module uses. Tests pass a stand-in."""

    def get_signing_key_from_jwt(self, token: str) -> object:
        """Return the key that signed ``token``."""


def auth_origin(auth_url: str) -> str:
    """Return the issuer and audience for a Neon Auth base URL.

    Args:
        auth_url: The Neon Auth URL, including its path. A trailing slash is ignored.

    Returns:
        ``scheme://host`` with no path.

    Raises:
        ValueError: The URL has no http(s) scheme or host.

    Example:
        >>> auth_origin("https://ep.example/neondb/auth/")
        'https://ep.example'
    """
    parsed = urlparse(auth_url.strip().rstrip("/"))
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Neon Auth URL must be an http(s) URL.")
    return f"{parsed.scheme}://{parsed.netloc}"


class NeonAuth:
    """Check Neon Auth bearer tokens against the published JWKS."""

    def __init__(self, auth_url: str, *, jwks_client: SigningKeys | None = None) -> None:
        """Create the checker.

        Args:
            auth_url: Neon Auth base URL. The JWKS URL is this plus ``/.well-known/jwks.json``.
            jwks_client: Key source. ``None`` fetches the JWKS URL and caches the keys.
        """
        base = auth_url.strip().rstrip("/")
        self.origin = auth_origin(base)
        self._jwks = jwks_client or jwt.PyJWKClient(f"{base}/.well-known/jwks.json")
        self._lock = threading.Lock()

    def user_id(self, token: str) -> str:
        """Return the Neon user id (``sub``) from a valid token.

        Args:
            token: The JWT, without the ``Bearer`` prefix.

        Returns:
            The user id as a lowercase UUID string.

        Raises:
            UnauthenticatedError: The token is wrong or expired (401).
        """
        return _user_id(self._claims(token))

    def account(self, token: str) -> NeonAccount:
        """Return the account named by a valid token.

        Args:
            token: The JWT, without the ``Bearer`` prefix.

        Returns:
            The account built from the token's claims.

        Raises:
            UnauthenticatedError: The token is wrong or expired (401).

        Example:
            >>> account = neon.account(token)  # doctest: +SKIP
            >>> account.email  # doctest: +SKIP
            'ada@example.com'
        """
        claims = self._claims(token)
        email = claims.get("email")
        email = email.strip().lower() if isinstance(email, str) else ""
        name = claims.get("name")
        display_name = name.strip() if isinstance(name, str) and name.strip() else ""
        return NeonAccount(
            id=_user_id(claims),
            email=email,
            display_name=display_name or email.partition("@")[0],
            created_at=_created_at(claims),
        )

    def _claims(self, token: str) -> dict[str, Any]:
        """Check the signature, issuer, audience, and expiry, then return the claims."""
        try:
            with self._lock:
                signing_key = self._jwks.get_signing_key_from_jwt(token)
                key = cast(Any, getattr(signing_key, "key", signing_key))
                payload = jwt.decode(
                    token,
                    key,
                    algorithms=["EdDSA"],
                    issuer=self.origin,
                    audience=self.origin,
                    options={"require": ["exp", "sub", "iss", "aud"]},
                )
        except jwt.ExpiredSignatureError as error:
            raise UnauthenticatedError("Please log in again.") from error
        except (jwt.PyJWTError, PyJWKClientError, URLError, TimeoutError) as error:
            raise UnauthenticatedError("Invalid login token.") from error
        if not isinstance(payload, dict):
            raise UnauthenticatedError("Invalid login token.")
        return payload


def _user_id(claims: dict[str, Any]) -> str:
    """Return ``sub`` as a lowercase UUID string, or raise a 401."""
    sub = claims.get("sub")
    if not isinstance(sub, str):
        raise UnauthenticatedError("Invalid login token.")
    try:
        return str(uuid.UUID(sub))
    except ValueError as error:
        raise UnauthenticatedError("Invalid login token.") from error


def _created_at(claims: dict[str, Any]) -> datetime:
    """Return ``createdAt`` as UTC, else the issue time, else now."""
    created = claims.get("createdAt")
    if isinstance(created, str):
        try:
            parsed = datetime.fromisoformat(created)
        except ValueError:
            parsed = None
        if parsed is not None:
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    issued = claims.get("iat")
    if isinstance(issued, int | float):
        return datetime.fromtimestamp(issued, UTC)
    return datetime.now(UTC)

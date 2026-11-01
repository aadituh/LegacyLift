"""Verify a Neon Auth JWT and return the signed-in user id.

The web app signs in with Neon Auth and sends ``Authorization: Bearer`` from
``authClient.token()``. That token is EdDSA, not the API's own HS256 login
token. The public keys come from ``{neon auth url}/.well-known/jwks.json``.
The issuer and audience are the origin of that URL (no path). The user id is
the ``sub`` claim, which matches ``neon_auth."user".id``.
"""

import threading
import uuid
from typing import Any, Protocol, cast
from urllib.error import URLError
from urllib.parse import urlparse

import jwt
from jwt.exceptions import PyJWKClientError

from legacylift.errors import UnauthenticatedError


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
        sub = payload.get("sub") if isinstance(payload, dict) else None
        if not isinstance(sub, str):
            raise UnauthenticatedError("Invalid login token.")
        try:
            return str(uuid.UUID(sub))
        except ValueError as error:
            raise UnauthenticatedError("Invalid login token.") from error

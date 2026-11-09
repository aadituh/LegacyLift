"""Neon Auth JWT checks, with a local Ed25519 key instead of the network JWKS."""

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from legacylift.errors import UnauthenticatedError
from legacylift.services.neon_auth import NeonAuth

USER_ID = "860dc360-609f-4b7d-9e70-ec93fe6414d3"
ORIGIN = "https://auth.example"


class _Key:
    def __init__(self, key: object) -> None:
        self.key = key


class _JWKS:
    def __init__(self, key: object) -> None:
        self._key = key

    def get_signing_key_from_jwt(self, token: str) -> _Key:
        return _Key(self._key)


def _auth(private: Ed25519PrivateKey) -> NeonAuth:
    return NeonAuth(f"{ORIGIN}/neondb/auth", jwks_client=_JWKS(private.public_key()))


def _token(private: Ed25519PrivateKey, *, exp: datetime, issuer: str = ORIGIN) -> str:
    encoded = jwt.encode(
        {"sub": USER_ID, "iss": issuer, "aud": ORIGIN, "exp": exp},
        private,
        algorithm="EdDSA",
    )
    return encoded if isinstance(encoded, str) else encoded.decode()


def test_a_valid_token_returns_the_user_id():
    private = Ed25519PrivateKey.generate()
    auth = _auth(private)
    token = _token(private, exp=datetime.now(UTC) + timedelta(minutes=5))
    assert auth.user_id(token) == USER_ID


def test_an_expired_token_asks_the_caller_to_log_in_again():
    private = Ed25519PrivateKey.generate()
    auth = _auth(private)
    token = _token(private, exp=datetime.now(UTC) - timedelta(minutes=5))
    with pytest.raises(UnauthenticatedError, match="Please log in again."):
        auth.user_id(token)


def test_a_token_from_another_issuer_is_rejected():
    private = Ed25519PrivateKey.generate()
    auth = _auth(private)
    token = _token(
        private,
        exp=datetime.now(UTC) + timedelta(minutes=5),
        issuer="https://other.example",
    )
    with pytest.raises(UnauthenticatedError, match="Invalid login token."):
        auth.user_id(token)


def _signed(private: Ed25519PrivateKey, claims: dict[str, object]) -> str:
    base = {"sub": USER_ID, "iss": ORIGIN, "aud": ORIGIN}
    encoded = jwt.encode({**base, **claims}, private, algorithm="EdDSA")
    return encoded if isinstance(encoded, str) else encoded.decode()


def test_account_reads_email_name_and_created_at_from_the_token():
    private = Ed25519PrivateKey.generate()
    token = _signed(
        private,
        {
            "email": "Ada@Example.com",
            "name": "Ada Lovelace",
            "createdAt": "2026-11-09T01:30:00.000Z",
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
    )
    account = _auth(private).account(token)
    assert (account.id, account.email, account.display_name) == (
        USER_ID,
        "ada@example.com",
        "Ada Lovelace",
    )
    assert account.created_at == datetime(2026, 11, 9, 1, 30, tzinfo=UTC)


def test_account_falls_back_to_the_email_and_issue_time():
    private = Ed25519PrivateKey.generate()
    issued = datetime(2026, 11, 9, 2, 0, tzinfo=UTC)
    token = _signed(
        private,
        {
            "email": "grace@example.com",
            "iat": issued,
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
    )
    account = _auth(private).account(token)
    assert (account.display_name, account.created_at) == ("grace", issued)

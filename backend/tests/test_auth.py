"""Sign up, log in, and the token on GET /api/auth/me."""

import base64
import json
from datetime import UTC, datetime, timedelta

import jwt

from legacylift.errors import UnauthenticatedError

from helpers import make_client

SECRET = "test-token-secret-not-used-in-production"
ACCOUNT = {
    "email": "Ada@Example.com",
    "password": "correct horse 1",
    "display_name": "Ada Lovelace",
}


def register(client, **overrides):
    body = {**ACCOUNT, **overrides}
    return client.post("/api/auth/register", json=body)


def test_register_hides_the_password_and_stores_only_a_hash(tmp_path):
    client = make_client(tmp_path, token_secret=SECRET)
    response = register(client)
    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"id", "email", "display_name", "created_at"}
    assert body["email"] == "ada@example.com"
    assert body["display_name"] == "Ada Lovelace"
    assert "correct horse 1" not in response.text
    saved = (tmp_path / "users.json").read_text(encoding="utf-8")
    assert "correct horse 1" not in saved
    assert "password_hash" in saved


def test_used_email_is_409_and_a_weak_password_is_422(tmp_path):
    client = make_client(tmp_path, token_secret=SECRET)
    assert register(client).status_code == 201
    again = register(client, email="ADA@example.com")
    assert (again.status_code, again.json()["detail"]) == (
        409,
        "An account with this email already exists.",
    )
    weak = register(client, email="new@example.com", password="password")
    assert weak.status_code == 422
    assert weak.json()["detail"] == (
        "Password must be 8 to 128 characters and include a letter and a number."
    )


def test_login_returns_a_token_and_me_returns_the_user(tmp_path):
    client = make_client(tmp_path, token_secret=SECRET, token_ttl_seconds=3600)
    created = register(client).json()
    logged_in = client.post(
        "/api/auth/login",
        json={"email": "ada@example.com", "password": ACCOUNT["password"]},
    )
    assert logged_in.status_code == 200
    token = logged_in.json()["token"]
    assert logged_in.json()["expires_in"] == 3600
    assert ACCOUNT["password"] not in logged_in.text
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["id"] == created["id"]
    assert me.json()["email"] == "ada@example.com"
    assert "password" not in me.json()


def test_wrong_email_and_wrong_password_share_one_message(tmp_path):
    client = make_client(tmp_path, token_secret=SECRET)
    register(client)
    unknown = client.post(
        "/api/auth/login",
        json={"email": "missing@example.com", "password": ACCOUNT["password"]},
    )
    wrong = client.post(
        "/api/auth/login",
        json={"email": ACCOUNT["email"], "password": "correct horse 2"},
    )
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json() == wrong.json() == {"detail": "Invalid email or password."}


def test_missing_wrong_and_expired_tokens_are_401(tmp_path):
    client = make_client(tmp_path, token_secret=SECRET)
    missing = client.get("/api/auth/me")
    assert (missing.status_code, missing.json()["detail"]) == (401, "Missing login token.")
    wrong = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-token"})
    assert (wrong.status_code, wrong.json()["detail"]) == (401, "Invalid login token.")
    expired = jwt.encode(
        {"sub": "missing", "exp": datetime.now(UTC) - timedelta(seconds=30)},
        SECRET,
        algorithm="HS256",
    )
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert (response.status_code, response.json()["detail"]) == (401, "Please log in again.")


def test_login_required_projects_belong_to_the_signed_in_account(tmp_path):
    client = make_client(tmp_path, token_secret=SECRET, require_login=True)
    register(client)
    token = client.post(
        "/api/auth/login",
        json={"email": ACCOUNT["email"], "password": ACCOUNT["password"]},
    ).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.post("/api/projects", json={"name": "Hidden"}).status_code == 401
    created = client.post("/api/projects", json={"name": "Mine"}, headers=headers)
    assert created.status_code == 201
    assert client.get("/api/projects", headers=headers).json()["projects"][0]["name"] == "Mine"

    register(client, email="other@example.com", display_name="Other")
    other = client.post(
        "/api/auth/login",
        json={"email": "other@example.com", "password": ACCOUNT["password"]},
    ).json()["token"]
    other_headers = {"Authorization": f"Bearer {other}"}
    assert client.get("/api/projects", headers=other_headers).json() == {"projects": []}
    assert (
        client.get(f"/api/projects/{created.json()['id']}", headers=other_headers).status_code
        == 404
    )


ADA_ID = "860dc360-609f-4b7d-9e70-ec93fe6414d3"
OTHER_ID = "11111111-1111-4111-8111-111111111111"


def _eddsa_token(sub: str) -> str:
    """A JWT whose header says EdDSA. The route test stubs signature checks."""

    def part(value: dict[str, str]) -> str:
        raw = json.dumps(value, separators=(",", ":")).encode()
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    return f"{part({'alg': 'EdDSA', 'typ': 'JWT'})}.{part({'sub': sub})}.sig"


class _Neon:
    """Stand-in that accepts the two ids used below."""

    def user_id(self, token: str) -> str:
        payload = token.split(".")[1]
        pad = "=" * (-len(payload) % 4)
        sub = json.loads(base64.urlsafe_b64decode(payload + pad))["sub"]
        if sub not in {ADA_ID, OTHER_ID}:
            raise UnauthenticatedError("Invalid login token.")
        return sub


def test_neon_token_owns_the_project_and_hides_it_from_the_other_account(tmp_path):
    client = make_client(tmp_path)
    client.app.state.neon_auth = _Neon()
    ada = {"Authorization": f"Bearer {_eddsa_token(ADA_ID)}"}
    other = {"Authorization": f"Bearer {_eddsa_token(OTHER_ID)}"}
    created = client.post("/api/projects", json={"name": "Mine"}, headers=ada)
    assert created.status_code == 201
    project_id = created.json()["id"]
    assert client.get("/api/projects", headers=ada).json()["projects"][0]["name"] == "Mine"
    assert client.get("/api/projects", headers=other).json() == {"projects": []}
    assert client.get(f"/api/projects/{project_id}", headers=other).status_code == 404
    assert client.get("/api/projects").json()["projects"][0]["name"] == "Mine"


def test_bad_neon_token_is_401(tmp_path):
    client = make_client(tmp_path)
    client.app.state.neon_auth = _Neon()
    response = client.post(
        "/api/projects",
        json={"name": "Nope"},
        headers={"Authorization": f"Bearer {_eddsa_token('not-a-user')}"},
    )
    assert (response.status_code, response.json()["detail"]) == (401, "Invalid login token.")


def test_projects_made_before_login_have_no_owner_and_stay_hidden(tmp_path):
    open_client = make_client(tmp_path, token_secret=SECRET, require_login=False)
    created = open_client.post("/api/projects", json={"name": "Before"})
    assert created.status_code == 201
    saved = json.loads((tmp_path / "1.json").read_text(encoding="utf-8"))
    assert saved["owner_id"] is None

    locked = make_client(tmp_path, token_secret=SECRET, require_login=True)
    register(locked)
    token = locked.post(
        "/api/auth/login",
        json={"email": ACCOUNT["email"], "password": ACCOUNT["password"]},
    ).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert locked.get("/api/projects", headers=headers).json() == {"projects": []}
    assert locked.get("/api/projects/1", headers=headers).status_code == 404

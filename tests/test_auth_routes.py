from uuid import uuid4

from jwks_server import sign_google_token
from sqlmodel import select

from app.auth.session import verify_session_token
from app.core.config import settings
from app.models.user import User


def test_login_creates_the_user(client, session, jwks_server, monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_JWKS_URL", jwks_server.url)
    token = sign_google_token(jwks_server, sub="google-sub-1", email="new@example.com")

    response = client.post("/auth/login", json={"id_token": token})

    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "Authentication successful"
    assert body["session_token"]
    assert body["expires_in"] > 0
    assert body["user"]["email"] == "new@example.com"

    user = session.exec(select(User).where(User.email == "new@example.com")).one()
    assert user.google_sub == "google-sub-1"


def test_login_returns_a_session_token_for_the_user(client, session, jwks_server, monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_JWKS_URL", jwks_server.url)
    token = sign_google_token(jwks_server, sub="google-sub-1", email="new@example.com")

    response = client.post("/auth/login", json={"id_token": token})

    user = session.exec(select(User).where(User.email == "new@example.com")).one()
    payload = verify_session_token(response.json()["session_token"])

    assert payload["sub"] == str(user.id)
    assert payload["google_sub"] == "google-sub-1"
    assert payload["email"] == "new@example.com"


def test_login_uses_the_same_user_the_next_time(client, session, jwks_server, monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_JWKS_URL", jwks_server.url)
    token = sign_google_token(jwks_server, sub="google-sub-1", email="new@example.com")

    first = client.post("/auth/login", json={"id_token": token})
    second = client.post("/auth/login", json={"id_token": token})

    assert first.json()["user"]["id"] == second.json()["user"]["id"]
    assert len(session.exec(select(User)).all()) == 1


def test_login_fills_the_google_id_of_an_old_user(client, session, jwks_server, monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_JWKS_URL", jwks_server.url)
    old_user = User(id=uuid4(), name="Old Name", email="old@example.com")
    session.add(old_user)
    session.commit()

    token = sign_google_token(jwks_server, sub="google-sub-1", email="old@example.com")
    response = client.post("/auth/login", json={"id_token": token})

    assert response.status_code == 200
    # the id of the old user stays the same, so the favourites and playlists keep working
    assert response.json()["user"]["id"] == str(old_user.id)

    session.refresh(old_user)
    assert old_user.google_sub == "google-sub-1"


def test_login_rejects_a_bad_id_token(client, jwks_server, monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_JWKS_URL", jwks_server.url)
    token = sign_google_token(jwks_server, aud="another-client")

    response = client.post("/auth/login", json={"id_token": token})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid google id token"


def test_login_needs_an_id_token(client):
    response = client.post("/auth/login", json={})

    assert response.status_code == 422


def test_current_user_returns_the_user_with_favourites(client, current_user):
    response = client.get("/auth/", headers={"Authorization": "Bearer test-token"})

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(current_user.id)
    assert body["name"] == "Test User"
    assert body["email"] == "test@example.com"
    assert body["favourites"] == []

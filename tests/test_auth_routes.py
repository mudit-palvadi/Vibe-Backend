from uuid import uuid4

from sqlmodel import select

from app.models.user import User


def test_login_creates_the_user(client, session, auth_headers, monkeypatch):
    new_sub = str(uuid4())
    new_payload = {
        "sub": new_sub,
        "email": "new@example.com",
        "user_metadata": {"full_name": "New User"},
    }
    monkeypatch.setattr("app.routes.auth_routes.verify_token", lambda token: new_payload)

    response = client.post("/auth/login", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["message"] == "Authentication successful"
    assert response.json()["user"]["email"] == "new@example.com"

    user = session.exec(select(User).where(User.email == "new@example.com")).one()
    assert str(user.id) == new_sub


def test_login_rekeys_the_user_found_by_email(client, session, auth_headers, token_payload):
    existing = User(id=uuid4(), name="Old Name", email=token_payload["email"])
    session.add(existing)
    session.commit()

    response = client.post("/auth/login", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["user"]["email"] == token_payload["email"]

    user = session.exec(select(User).where(User.email == token_payload["email"])).one()
    assert str(user.id) == token_payload["sub"]


def test_login_rejects_a_bad_authorization_header(client):
    response = client.post("/auth/login", headers={"Authorization": "Bearer"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid authorization header"


def test_login_needs_a_token(client):
    response = client.post("/auth/login")

    assert response.status_code == 422


def test_current_user_returns_the_user_with_favourites(client, current_user):
    response = client.get("/auth/", headers={"Authorization": "Bearer test-token"})

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(current_user.id)
    assert body["name"] == "Test User"
    assert body["email"] == "test@example.com"
    assert body["favourites"] == []

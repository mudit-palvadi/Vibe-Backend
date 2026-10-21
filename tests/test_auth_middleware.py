from uuid import uuid4

from fastapi import HTTPException
from sqlmodel import select

from app.models.user import User


def test_the_middleware_finds_the_user_of_the_session(client, current_user):
    response = client.get("/auth/", headers={"Authorization": "Bearer test-token"})

    assert response.status_code == 200
    assert response.json()["id"] == str(current_user.id)


def test_the_middleware_needs_a_bearer_token(client):
    response = client.get("/auth/", headers={"Authorization": "Basic test-token"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid authorization format or token missing"


def test_the_middleware_needs_a_token_at_all(client):
    response = client.get("/auth/")

    assert response.status_code == 401


def test_the_middleware_rejects_a_session_token_it_cannot_check(client, monkeypatch):
    def broken_verify(token):
        raise HTTPException(status_code=401, detail="Invalid session token")

    monkeypatch.setattr("app.middleware.auth_middleware.verify_session_token", broken_verify)

    response = client.get("/auth/", headers={"Authorization": "Bearer broken-token"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid session token"


def test_the_middleware_rejects_a_session_token_without_a_user_id(client, monkeypatch):
    monkeypatch.setattr(
        "app.middleware.auth_middleware.verify_session_token", lambda token: {"email": "a@b.c"}
    )

    response = client.get("/auth/", headers={"Authorization": "Bearer test-token"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid session token payload"


def test_the_middleware_rejects_a_user_id_that_is_not_a_uuid(client, monkeypatch):
    monkeypatch.setattr(
        "app.middleware.auth_middleware.verify_session_token",
        lambda token: {"sub": "not-a-uuid"},
    )

    response = client.get("/auth/", headers={"Authorization": "Bearer test-token"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid user ID format"


def test_the_middleware_finds_the_user_by_the_google_id(client, session, monkeypatch):
    user = User(
        id=uuid4(),
        name="Test User",
        email="test@example.com",
        google_sub="google-sub-1",
    )
    session.add(user)
    session.commit()

    # the session token was made for another id
    monkeypatch.setattr(
        "app.middleware.auth_middleware.verify_session_token",
        lambda token: {"sub": str(uuid4()), "google_sub": "google-sub-1"},
    )

    response = client.get("/auth/", headers={"Authorization": "Bearer test-token"})

    assert response.status_code == 200
    assert response.json()["id"] == str(user.id)


def test_the_middleware_says_when_the_user_is_gone(client, session, monkeypatch):
    monkeypatch.setattr(
        "app.middleware.auth_middleware.verify_session_token",
        lambda token: {"sub": str(uuid4()), "google_sub": "a-google-sub-nobody-has"},
    )

    response = client.get("/auth/", headers={"Authorization": "Bearer test-token"})

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found!"


def test_the_middleware_does_not_make_a_user_that_is_gone(client, session, monkeypatch):
    monkeypatch.setattr(
        "app.middleware.auth_middleware.verify_session_token",
        lambda token: {"sub": str(uuid4()), "google_sub": "a-google-sub-nobody-has"},
    )

    client.get("/auth/", headers={"Authorization": "Bearer test-token"})

    assert session.exec(select(User)).all() == []

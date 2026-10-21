import pytest
from fastapi import HTTPException

from app.auth.session import verify_session_token
from app.core.config import settings


@pytest.fixture(autouse=True)
def mock_exchange(monkeypatch):
    """google is not called in the tests"""
    calls = {}

    def fake_exchange(refresh_token):
        calls["refresh_token"] = refresh_token
        return {"access_token": "new-access-token"}

    monkeypatch.setattr("app.routes.auth_routes.exchange_refresh_token", fake_exchange)
    return calls


def test_refresh_gives_a_new_session_token(client, current_user):
    response = client.post(
        "/auth/refresh",
        json={"refresh_token": "a-google-refresh-token"},
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "Session refreshed"
    assert body["session_token"]
    assert body["user"]["email"] == "test@example.com"

    payload = verify_session_token(body["session_token"])
    assert payload["sub"] == str(current_user.id)
    assert payload["google_sub"] == "google-sub-1"


def test_refresh_asks_google_about_the_refresh_token(client, current_user, mock_exchange):
    client.post(
        "/auth/refresh",
        json={"refresh_token": "a-google-refresh-token"},
        headers={"Authorization": "Bearer test-token"},
    )

    assert mock_exchange["refresh_token"] == "a-google-refresh-token"


def test_refresh_says_when_the_google_session_is_over(client, current_user, monkeypatch):
    def broken_exchange(refresh_token):
        raise HTTPException(status_code=401, detail="Google session is not valid anymore")

    monkeypatch.setattr("app.routes.auth_routes.exchange_refresh_token", broken_exchange)

    response = client.post(
        "/auth/refresh",
        json={"refresh_token": "a-dead-refresh-token"},
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Google session is not valid anymore"


def test_refresh_needs_a_session_token(client, current_user):
    response = client.post("/auth/refresh", json={"refresh_token": "a-google-refresh-token"})

    assert response.status_code == 401


def test_refresh_needs_a_refresh_token(client, current_user):
    response = client.post(
        "/auth/refresh", json={}, headers={"Authorization": "Bearer test-token"}
    )

    assert response.status_code == 422


def test_refresh_keeps_the_session_issuer(client, current_user):
    response = client.post(
        "/auth/refresh",
        json={"refresh_token": "a-google-refresh-token"},
        headers={"Authorization": "Bearer test-token"},
    )

    payload = verify_session_token(response.json()["session_token"])
    assert payload["iss"] == settings.SESSION_ISSUER

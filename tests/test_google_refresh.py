import httpx
import pytest
from fastapi import HTTPException

from app.auth.google import exchange_refresh_token
from app.core.config import settings


def _fake_post(monkeypatch, status_code: int, payload: dict | None = None):
    calls = {}

    def fake_post(url, data=None, timeout=None):
        calls["url"] = url
        calls["data"] = data
        return httpx.Response(status_code, json=payload or {})

    monkeypatch.setattr("app.auth.google.httpx.post", fake_post)
    return calls


def test_exchange_refresh_token_returns_the_google_tokens(monkeypatch):
    calls = _fake_post(monkeypatch, 200, {"access_token": "new-access-token", "expires_in": 3600})

    result = exchange_refresh_token("a-refresh-token")

    assert result["access_token"] == "new-access-token"
    assert calls["url"] == settings.GOOGLE_TOKEN_URL
    assert calls["data"]["grant_type"] == "refresh_token"
    assert calls["data"]["refresh_token"] == "a-refresh-token"
    assert calls["data"]["client_id"] == settings.GOOGLE_CLIENT_ID


def test_exchange_refresh_token_sends_the_client_secret_when_there_is_one(monkeypatch):
    calls = _fake_post(monkeypatch, 200, {"access_token": "new-access-token"})
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", "the-client-secret")

    exchange_refresh_token("a-refresh-token")

    assert calls["data"]["client_secret"] == "the-client-secret"


def test_exchange_refresh_token_leaves_out_the_client_secret_when_there_is_none(monkeypatch):
    calls = _fake_post(monkeypatch, 200, {"access_token": "new-access-token"})
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", "")

    exchange_refresh_token("a-refresh-token")

    assert "client_secret" not in calls["data"]


def test_exchange_refresh_token_rejects_a_dead_refresh_token(monkeypatch):
    _fake_post(monkeypatch, 400, {"error": "invalid_grant"})

    with pytest.raises(HTTPException) as error:
        exchange_refresh_token("a-dead-refresh-token")

    assert error.value.status_code == 401
    assert error.value.detail == "Google session is not valid anymore"


def test_exchange_refresh_token_reports_a_google_outage(monkeypatch):
    _fake_post(monkeypatch, 503, {})

    with pytest.raises(HTTPException) as error:
        exchange_refresh_token("a-refresh-token")

    assert error.value.status_code == 502

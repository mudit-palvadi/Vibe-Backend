from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException

from app.auth.google import verify_google_id_token
from app.core.config import settings


def _google_token(jwks_server, drop: tuple[str, ...] = (), **overrides) -> str:
    payload = {
        "sub": "google-sub-1",
        "email": "someone@gmail.com",
        "name": "Someone",
        "iss": "https://accounts.google.com",
        "aud": settings.GOOGLE_CLIENT_ID,
        "exp": int((datetime.now(UTC) + timedelta(hours=1)).timestamp()),
    }
    payload.update(overrides)
    for claim in drop:
        payload.pop(claim, None)
    return jwks_server.sign(payload)


def test_verify_google_id_token_returns_the_account(jwks_server, monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_JWKS_URL", jwks_server.url)

    identity = verify_google_id_token(_google_token(jwks_server))

    assert identity.sub == "google-sub-1"
    assert identity.email == "someone@gmail.com"
    assert identity.name == "Someone"


def test_verify_google_id_token_falls_back_to_the_email_for_the_name(jwks_server, monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_JWKS_URL", jwks_server.url)
    token = _google_token(jwks_server, name=None)

    identity = verify_google_id_token(token)

    assert identity.name == "someone"


def test_verify_google_id_token_rejects_a_token_of_another_client(jwks_server, monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_JWKS_URL", jwks_server.url)
    token = _google_token(jwks_server, aud="another-client")

    with pytest.raises(HTTPException) as error:
        verify_google_id_token(token)

    assert error.value.status_code == 401
    assert error.value.detail == "Invalid google id token"


def test_verify_google_id_token_rejects_an_unknown_issuer(jwks_server, monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_JWKS_URL", jwks_server.url)
    token = _google_token(jwks_server, iss="https://accounts.evil.example")

    with pytest.raises(HTTPException) as error:
        verify_google_id_token(token)

    assert error.value.status_code == 401
    assert error.value.detail == "Invalid google id token issuer"


def test_verify_google_id_token_needs_a_sub_and_an_email(jwks_server, monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_JWKS_URL", jwks_server.url)

    with pytest.raises(HTTPException) as error:
        verify_google_id_token(_google_token(jwks_server, drop=("sub",)))

    assert error.value.detail == "Invalid google id token payload"

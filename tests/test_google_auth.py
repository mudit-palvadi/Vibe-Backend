from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from jwks_server import sign_google_token

from app.auth.google import verify_google_id_token
from app.core.config import settings


def test_verify_google_id_token_returns_the_account(jwks_server, monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_JWKS_URL", jwks_server.url)

    identity = verify_google_id_token(sign_google_token(jwks_server))

    assert identity.sub == "google-sub-1"
    assert identity.email == "someone@gmail.com"
    assert identity.name == "Someone"


def test_verify_google_id_token_falls_back_to_the_email_for_the_name(jwks_server, monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_JWKS_URL", jwks_server.url)
    token = sign_google_token(jwks_server, name=None)

    identity = verify_google_id_token(token)

    assert identity.name == "someone"


def test_verify_google_id_token_rejects_a_token_of_another_client(jwks_server, monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_JWKS_URL", jwks_server.url)
    token = sign_google_token(jwks_server, aud="another-client")

    with pytest.raises(HTTPException) as error:
        verify_google_id_token(token)

    assert error.value.status_code == 401
    assert error.value.detail == "Invalid google id token"


def test_verify_google_id_token_rejects_an_unknown_issuer(jwks_server, monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_JWKS_URL", jwks_server.url)
    token = sign_google_token(jwks_server, iss="https://accounts.evil.example")

    with pytest.raises(HTTPException) as error:
        verify_google_id_token(token)

    assert error.value.status_code == 401
    assert error.value.detail == "Invalid google id token issuer"


def test_verify_google_id_token_needs_a_sub_and_an_email(jwks_server, monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_JWKS_URL", jwks_server.url)

    with pytest.raises(HTTPException) as error:
        verify_google_id_token(sign_google_token(jwks_server, drop=("sub",)))

    assert error.value.detail == "Invalid google id token payload"


def test_verify_google_id_token_rejects_an_expired_token(jwks_server, monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_JWKS_URL", jwks_server.url)
    expired = datetime.now(UTC) - timedelta(hours=1)
    token = sign_google_token(jwks_server, exp=int(expired.timestamp()))

    with pytest.raises(HTTPException) as error:
        verify_google_id_token(token)

    assert error.value.status_code == 401
    assert error.value.detail == "Invalid google id token"

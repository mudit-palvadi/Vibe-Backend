import jwt
import pytest
from fastapi import HTTPException

from app.auth.session import create_session_token, verify_session_token
from app.core.config import settings


def _create():
    return create_session_token(
        user_id="11111111-1111-4111-8111-111111111111",
        google_sub="google-sub-1",
        email="someone@gmail.com",
        name="Someone",
    )


def test_create_session_token_returns_a_token_and_the_seconds_left():
    token, expires_in = _create()

    assert token.count(".") == 2
    assert expires_in == settings.SESSION_TTL_DAYS * 24 * 60 * 60


def test_verify_session_token_returns_the_claims():
    token, _ = _create()

    payload = verify_session_token(token)

    assert payload["sub"] == "11111111-1111-4111-8111-111111111111"
    assert payload["google_sub"] == "google-sub-1"
    assert payload["email"] == "someone@gmail.com"
    assert payload["name"] == "Someone"
    assert payload["iss"] == settings.SESSION_ISSUER


def test_verify_session_token_rejects_a_token_signed_with_another_secret():
    token = jwt.encode(
        {"sub": "someone", "iss": settings.SESSION_ISSUER},
        "another-secret-that-is-long-enough-123",
        algorithm="HS256",
    )

    with pytest.raises(HTTPException) as error:
        verify_session_token(token)

    assert error.value.status_code == 401
    assert error.value.detail == "Invalid session token"


def test_verify_session_token_rejects_an_expired_token():
    token = jwt.encode(
        {
            "sub": "someone",
            "iss": settings.SESSION_ISSUER,
            "exp": 1000000000,
        },
        settings.SESSION_SECRET,
        algorithm="HS256",
    )

    with pytest.raises(HTTPException) as error:
        verify_session_token(token)

    assert error.value.status_code == 401


def test_verify_session_token_rejects_a_token_of_another_issuer():
    token = jwt.encode(
        {"sub": "someone", "iss": "some-other-service"},
        settings.SESSION_SECRET,
        algorithm="HS256",
    )

    with pytest.raises(HTTPException) as error:
        verify_session_token(token)

    assert error.value.status_code == 401


def test_verify_session_token_rejects_a_tampered_token():
    token, _ = _create()
    header, payload, signature = token.split(".")

    with pytest.raises(HTTPException) as error:
        verify_session_token(f"{header}.{payload}x.{signature}")

    assert error.value.status_code == 401

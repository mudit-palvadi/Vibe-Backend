from datetime import UTC, datetime, timedelta

import jwt
import pytest
from jwks_server import build_key_pair

from app.auth.jwks import verify_jwt


def test_verify_jwt_returns_the_payload(jwks_server):
    token = jwks_server.sign({"sub": "abc", "hello": "world"})

    payload = verify_jwt(token, jwks_url=jwks_server.url)

    assert payload["sub"] == "abc"
    assert payload["hello"] == "world"


def test_verify_jwt_rejects_a_token_signed_by_another_key(jwks_server):
    other_key = build_key_pair()
    token = jwt.encode(
        {"sub": "abc"},
        other_key,
        algorithm="RS256",
        headers={"kid": jwks_server.kid},
    )

    with pytest.raises(jwt.InvalidSignatureError):
        verify_jwt(token, jwks_url=jwks_server.url)


def test_verify_jwt_rejects_an_unknown_key_id(jwks_server):
    token = jwks_server.sign({"sub": "abc"}, kid="a-key-that-does-not-exist")

    with pytest.raises(jwt.PyJWKClientError):
        verify_jwt(token, jwks_url=jwks_server.url)


def test_verify_jwt_rejects_an_expired_token(jwks_server):
    expired = datetime.now(UTC) - timedelta(minutes=5)
    token = jwks_server.sign({"sub": "abc", "exp": int(expired.timestamp())})

    with pytest.raises(jwt.ExpiredSignatureError):
        verify_jwt(token, jwks_url=jwks_server.url)


def test_verify_jwt_checks_the_audience(jwks_server):
    token = jwks_server.sign({"sub": "abc", "aud": "another-client"})

    with pytest.raises(jwt.InvalidAudienceError):
        verify_jwt(token, jwks_url=jwks_server.url, audience="my-client-id")

    token = jwks_server.sign({"sub": "abc", "aud": "my-client-id"})
    payload = verify_jwt(token, jwks_url=jwks_server.url, audience="my-client-id")

    assert payload["sub"] == "abc"


def test_verify_jwt_checks_the_issuer(jwks_server):
    token = jwks_server.sign({"sub": "abc", "iss": "https://someone-else.example"})

    with pytest.raises(jwt.InvalidIssuerError):
        verify_jwt(token, jwks_url=jwks_server.url, issuer="https://accounts.google.com")

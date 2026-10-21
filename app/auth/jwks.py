from functools import lru_cache

import jwt
from jwt import PyJWKClient


@lru_cache(maxsize=8)
def _jwk_client(jwks_url: str) -> PyJWKClient:
    """the jwks of a provider changes rarely, so the keys are cached for a while"""
    return PyJWKClient(jwks_url, lifespan=300)


def verify_jwt(
    token: str,
    *,
    jwks_url: str,
    audience: str | None = None,
    issuer: str | None = None,
    algorithms: tuple[str, ...] = ("RS256",),
) -> dict:
    """verifies a jwt that was signed by the provider that owns the jwks"""
    signing_key = _jwk_client(jwks_url).get_signing_key_from_jwt(token).key

    return jwt.decode(
        token,
        signing_key,
        algorithms=list(algorithms),
        audience=audience,
        issuer=issuer,
        options={
            "verify_aud": audience is not None,
            "verify_iss": issuer is not None,
        },
    )

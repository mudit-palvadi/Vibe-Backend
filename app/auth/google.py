from dataclasses import dataclass

import httpx
from fastapi import HTTPException

from app.auth.jwks import verify_jwt
from app.core.config import settings

ALLOWED_ISSUERS = ("https://accounts.google.com", "accounts.google.com")


@dataclass(frozen=True)
class GoogleIdentity:
    """the google account that signed in"""

    sub: str
    email: str
    name: str
    picture: str | None = None


def verify_google_id_token(id_token: str) -> GoogleIdentity:
    """checks the google id token and returns the google account behind it"""
    try:
        payload = verify_jwt(
            id_token,
            jwks_url=settings.GOOGLE_JWKS_URL,
            audience=settings.GOOGLE_CLIENT_ID,
        )
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid google id token") from e

    if payload.get("iss") not in ALLOWED_ISSUERS:
        raise HTTPException(status_code=401, detail="Invalid google id token issuer")

    sub = payload.get("sub")
    email = payload.get("email")

    if not sub or not email:
        raise HTTPException(status_code=401, detail="Invalid google id token payload")

    return GoogleIdentity(
        sub=sub,
        email=email,
        name=payload.get("name") or email.split("@")[0],
        picture=payload.get("picture"),
    )


def exchange_refresh_token(refresh_token: str) -> dict:
    """trades the google refresh token of the client for a new google access token"""
    data = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }

    if settings.GOOGLE_CLIENT_SECRET:
        data["client_secret"] = settings.GOOGLE_CLIENT_SECRET

    try:
        response = httpx.post(settings.GOOGLE_TOKEN_URL, data=data, timeout=10)
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail="Could not reach google") from e

    if response.status_code == 200:
        return response.json()

    if response.status_code >= 500:
        raise HTTPException(status_code=502, detail="Google is not answering right now")

    # google says invalid_grant when the refresh token is not valid anymore
    raise HTTPException(status_code=401, detail="Google session is not valid anymore")

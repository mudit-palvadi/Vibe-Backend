from dataclasses import dataclass

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

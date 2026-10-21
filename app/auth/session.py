from datetime import UTC, datetime, timedelta

import jwt
from fastapi import HTTPException

from app.core.config import settings
from app.core.secrets import session_secret


def create_session_token(
    *, user_id: str, google_sub: str, email: str, name: str
) -> tuple[str, int]:
    """signs the session token we hand out after a google login"""
    now = datetime.now(UTC)
    expires_at = now + timedelta(days=settings.SESSION_TTL_DAYS)

    payload = {
        "sub": user_id,
        "google_sub": google_sub,
        "email": email,
        "name": name,
        "iss": settings.SESSION_ISSUER,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }

    token = jwt.encode(payload, session_secret(), algorithm="HS256")

    return token, int((expires_at - now).total_seconds())


def verify_session_token(token: str) -> dict:
    """checks the session token that we signed ourselves"""
    try:
        return jwt.decode(
            token,
            session_secret(),
            algorithms=["HS256"],
            issuer=settings.SESSION_ISSUER,
        )
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid session token") from e

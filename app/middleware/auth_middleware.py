from uuid import UUID

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session, select

from app.auth.session import verify_session_token
from app.db.database import get_session
from app.models.user import User

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_session),
) -> User:
    if not credentials or credentials.scheme != "Bearer":
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization format or token missing",
        )

    payload = verify_session_token(credentials.credentials)

    user_id = payload.get("sub")
    google_sub = payload.get("google_sub")

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid session token payload")

    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid user ID format") from None

    user = db.exec(select(User).where(User.id == user_uuid)).first()

    if not user and google_sub:
        # the user is also found by the google id, so an old session still works
        user = db.exec(select(User).where(User.google_sub == google_sub)).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found!")

    return user

from uuid import UUID

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session, select

from app.auth.jwt_handler import verify_token
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

    token = credentials.credentials
    payload = verify_token(token)

    sub = payload.get("sub")
    email = payload.get("email")
    name = payload.get("user_metadata", {}).get("full_name", "User")

    if not sub or not email:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    try:
        user_uuid = UUID(sub)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid user ID format") from None

    # Ensure user exists in db and has correct UUID
    user = db.exec(select(User).where(User.id == user_uuid)).first()
    if not user:
        user_by_email = db.exec(select(User).where(User.email == email)).first()
        if user_by_email:
            user_by_email.id = user_uuid
            db.add(user_by_email)
            db.commit()
            db.refresh(user_by_email)
            user = user_by_email
        else:
            new_user = User(id=user_uuid, name=name, email=email)
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            user = new_user

    return user

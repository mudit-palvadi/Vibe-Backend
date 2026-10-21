from uuid import UUID

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.session import verify_session_token
from app.repositories.dependencies import get_user_repository
from app.repositories.protocols import UserRepository
from app.repositories.records import UserRecord

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    users: UserRepository = Depends(get_user_repository),
) -> UserRecord:
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
        UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid user ID format") from None

    user = users.get_by_id(user_id)

    if not user and google_sub:
        # the user is also found by the google id, so an old session still works
        user = users.get_by_google_sub(google_sub)

    if not user:
        raise HTTPException(status_code=404, detail="User not found!")

    return user

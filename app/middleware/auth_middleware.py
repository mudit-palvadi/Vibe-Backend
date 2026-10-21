from uuid import UUID

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.session import verify_session_token
from app.repositories.dependencies import get_user_repository
from app.repositories.protocols import UserRepository
from app.repositories.records import UserRecord

security = HTTPBearer(auto_error=False)

# cloudfront signs the request it sends to the lambda, so the header of the
# viewer is not the one that arrives, the token comes in its own header
SESSION_HEADER = "x-vibe-auth"


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    users: UserRepository = Depends(get_user_repository),
) -> UserRecord:
    token = request.headers.get(SESSION_HEADER)

    if not token and credentials and credentials.scheme == "Bearer":
        token = credentials.credentials

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization format or token missing",
        )

    payload = verify_session_token(token)

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

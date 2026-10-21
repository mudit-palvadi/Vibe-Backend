from fastapi import APIRouter, Depends

from app.auth.google import exchange_refresh_token, verify_google_id_token
from app.auth.session import create_session_token
from app.middleware.auth_middleware import get_current_user
from app.repositories.dependencies import get_favourite_repository, get_user_repository
from app.repositories.protocols import FavouriteRepository, UserRepository
from app.repositories.records import UserRecord
from app.schemas.user import (
    AuthLoginResponse,
    AuthRefreshResponse,
    LoginRequest,
    RefreshRequest,
    UserWithFavouritesResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=AuthLoginResponse)
def google_login(
    request: LoginRequest,
    users: UserRepository = Depends(get_user_repository),
):
    identity = verify_google_id_token(request.id_token)

    user = users.get_by_google_sub(identity.sub)

    if not user:
        # an account that was made with supabase is found by the email
        user = users.get_by_email(identity.email)

        if user:
            user = users.set_google_sub(user.id, identity.sub)

    if not user:
        user = users.create(name=identity.name, email=identity.email, google_sub=identity.sub)

    session_token, expires_in = create_session_token(
        user_id=user.id,
        google_sub=identity.sub,
        email=user.email,
        name=user.name,
    )

    return {
        "message": "Authentication successful",
        "session_token": session_token,
        "expires_in": expires_in,
        "user": {"id": user.id, "name": user.name, "email": user.email},
    }


@router.post("/refresh", response_model=AuthRefreshResponse)
def refresh_session(
    request: RefreshRequest,
    current_user: UserRecord = Depends(get_current_user),
):
    # google only hands out a new access token here, so the client keeps the refresh token
    exchange_refresh_token(request.refresh_token)

    session_token, expires_in = create_session_token(
        user_id=current_user.id,
        google_sub=current_user.google_sub or "",
        email=current_user.email,
        name=current_user.name,
    )

    return {
        "message": "Session refreshed",
        "session_token": session_token,
        "expires_in": expires_in,
        "user": {
            "id": current_user.id,
            "name": current_user.name,
            "email": current_user.email,
        },
    }


@router.get("/", response_model=UserWithFavouritesResponse)
def current_user_data(
    current_user: UserRecord = Depends(get_current_user),
    favourites: FavouriteRepository = Depends(get_favourite_repository),
):
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "created_at": current_user.created_at,
        "updated_at": current_user.updated_at,
        "favourites": favourites.list_for_user(current_user.id),
    }

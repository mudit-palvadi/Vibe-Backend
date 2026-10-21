from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import joinedload
from sqlmodel import Session, select

from app.auth.google import exchange_refresh_token, verify_google_id_token
from app.auth.session import create_session_token
from app.db.database import get_session
from app.middleware.auth_middleware import get_current_user
from app.models.user import User
from app.schemas.user import (
    AuthLoginResponse,
    AuthRefreshResponse,
    LoginRequest,
    RefreshRequest,
    UserWithFavouritesResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=AuthLoginResponse)
def google_login(request: LoginRequest, session: Session = Depends(get_session)):
    identity = verify_google_id_token(request.id_token)

    user = session.exec(select(User).where(User.google_sub == identity.sub)).first()

    if not user:
        # an account that was made with supabase is found by the email
        user = session.exec(select(User).where(User.email == identity.email)).first()

        if user:
            user.google_sub = identity.sub
            session.add(user)
            session.commit()
            session.refresh(user)

    if not user:
        user = User(name=identity.name, email=identity.email, google_sub=identity.sub)
        session.add(user)
        session.commit()
        session.refresh(user)

    session_token, expires_in = create_session_token(
        user_id=str(user.id),
        google_sub=identity.sub,
        email=user.email,
        name=user.name,
    )

    return {
        "message": "Authentication successful",
        "session_token": session_token,
        "expires_in": expires_in,
        "user": {"id": str(user.id), "name": user.name, "email": user.email},
    }


@router.post("/refresh", response_model=AuthRefreshResponse)
def refresh_session(
    request: RefreshRequest,
    current_user: User = Depends(get_current_user),
):
    # google only hands out a new access token here, so the client keeps the refresh token
    exchange_refresh_token(request.refresh_token)

    session_token, expires_in = create_session_token(
        user_id=str(current_user.id),
        google_sub=current_user.google_sub or "",
        email=current_user.email,
        name=current_user.name,
    )

    return {
        "message": "Session refreshed",
        "session_token": session_token,
        "expires_in": expires_in,
        "user": {
            "id": str(current_user.id),
            "name": current_user.name,
            "email": current_user.email,
        },
    }


@router.get("/", response_model=UserWithFavouritesResponse)
def current_user_data(
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    user = db.exec(
        select(User).where(User.id == current_user.id).options(joinedload(User.favourites))
    ).first()

    if not user:
        raise HTTPException(404, "User not found!")

    return user

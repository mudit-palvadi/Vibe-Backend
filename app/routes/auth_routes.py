from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import joinedload
from sqlmodel import Session, select

from app.auth.jwt_handler import verify_token
from app.db.database import get_session
from app.middleware.auth_middleware import get_current_user
from app.models.user import User
from app.schemas.user import AuthLoginResponse, UserWithFavouritesResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=AuthLoginResponse)
def google_auth(authorization: str = Header(), session: Session = Depends(get_session)):

    try:
        token = authorization.split(" ")[1]

    except Exception:
        raise HTTPException(status_code=401, detail="Invalid authorization header") from None

    payload = verify_token(token)
    email = payload["email"]
    name = payload.get("user_metadata", {}).get("full_name", "User")
    user_sub = UUID(payload["sub"])
    user = session.exec(select(User).where(User.email == email)).first()

    if not user:
        user = User(id=user_sub, name=name, email=email)
        session.add(user)
        session.commit()
        session.refresh(user)
    elif user.id != user_sub:
        user.id = user_sub
        session.add(user)
        session.commit()
        session.refresh(user)

    return {
        "message": "Authentication successful",
        "user": {"id": str(user.id), "name": user.name, "email": user.email},
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

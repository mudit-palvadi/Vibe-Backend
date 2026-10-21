from datetime import datetime

from pydantic import BaseModel

from app.schemas.song import SongResponse


class UserResponse(BaseModel):
    id: str
    name: str
    email: str

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    id_token: str


class RefreshRequest(BaseModel):
    refresh_token: str


class AuthLoginResponse(BaseModel):
    message: str
    session_token: str
    expires_in: int
    user: UserResponse


class AuthRefreshResponse(BaseModel):
    message: str
    session_token: str
    expires_in: int
    user: UserResponse


class FavouriteResponse(BaseModel):
    id: str
    song_id: str
    user_id: str
    song: SongResponse

    model_config = {"from_attributes": True}


class UserWithFavouritesResponse(BaseModel):
    id: str
    name: str
    email: str
    created_at: datetime
    updated_at: datetime
    favourites: list[FavouriteResponse]

    model_config = {"from_attributes": True}

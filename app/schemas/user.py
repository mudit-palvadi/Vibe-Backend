from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.song import SongResponse


class UserResponse(BaseModel):
    id: UUID
    name: str
    email: str

    model_config = {"from_attributes": True}


class AuthLoginResponse(BaseModel):
    message: str
    user: UserResponse


class FavouriteResponse(BaseModel):
    id: str
    song_id: str
    user_id: UUID
    song: SongResponse

    model_config = {"from_attributes": True}


class UserWithFavouritesResponse(BaseModel):
    id: UUID
    name: str
    email: str
    created_at: datetime
    updated_at: datetime
    favourites: list[FavouriteResponse]

    model_config = {"from_attributes": True}

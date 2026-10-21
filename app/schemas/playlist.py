from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.song import SongResponse


class PlaylistCreate(BaseModel):
    name: str = Field(..., max_length=255)
    description: str | None = None
    thumbnail_url: str | None = Field(default=None, max_length=512)


class AddPlaylistSong(BaseModel):
    playlist_id: UUID
    song_id: str


class PlaylistResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    description: str | None = None
    thumbnail_url: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PlaylistWithSongsResponse(PlaylistResponse):
    songs: list[SongResponse] = []

    model_config = {"from_attributes": True}

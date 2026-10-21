from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class UserRecord:
    id: str
    name: str
    email: str
    google_sub: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True)
class SongRecord:
    id: str
    song_name: str
    artist: str
    song_url: str
    thumbnail_url: str
    tags: str


@dataclass(frozen=True)
class PlaylistRecord:
    id: str
    user_id: str
    name: str
    description: str | None = None
    thumbnail_url: str | None = None
    created_at: datetime | None = None


@dataclass(frozen=True)
class FavouriteRecord:
    id: str
    song_id: str
    user_id: str


@dataclass(frozen=True)
class FavouriteWithSong:
    id: str
    song_id: str
    user_id: str
    song: SongRecord

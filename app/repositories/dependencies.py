from fastapi import Depends
from sqlmodel import Session

from app.db.database import get_session
from app.repositories.protocols import (
    FavouriteRepository,
    PlaylistRepository,
    SongRepository,
    UserRepository,
)
from app.repositories.sqlmodel_repositories import (
    SqlModelFavouriteRepository,
    SqlModelPlaylistRepository,
    SqlModelSongRepository,
    SqlModelUserRepository,
)


def get_user_repository(session: Session = Depends(get_session)) -> UserRepository:
    return SqlModelUserRepository(session)


def get_song_repository(session: Session = Depends(get_session)) -> SongRepository:
    return SqlModelSongRepository(session)


def get_playlist_repository(session: Session = Depends(get_session)) -> PlaylistRepository:
    return SqlModelPlaylistRepository(session)


def get_favourite_repository(session: Session = Depends(get_session)) -> FavouriteRepository:
    return SqlModelFavouriteRepository(session)

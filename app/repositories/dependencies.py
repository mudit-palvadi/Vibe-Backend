import boto3
from fastapi import Depends
from sqlmodel import Session

from app.core.config import settings
from app.db.database import get_session
from app.repositories.dynamodb_repositories import (
    DynamoDbFavouriteRepository,
    DynamoDbPlaylistRepository,
    DynamoDbSongRepository,
    DynamoDbUserRepository,
)
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

_table = None


def get_dynamodb_table():
    """the table is made on the first use, so the app starts without aws keys"""
    global _table
    if _table is None:
        resource = boto3.resource("dynamodb", region_name=settings.AWS_REGION)
        _table = resource.Table(settings.DYNAMODB_TABLE_NAME)
    return _table


def get_user_repository(session: Session | None = Depends(get_session)) -> UserRepository:
    if settings.DB_BACKEND == "dynamodb":
        return DynamoDbUserRepository(get_dynamodb_table())

    return SqlModelUserRepository(session)


def get_song_repository(session: Session | None = Depends(get_session)) -> SongRepository:
    if settings.DB_BACKEND == "dynamodb":
        return DynamoDbSongRepository(get_dynamodb_table())

    return SqlModelSongRepository(session)


def get_playlist_repository(
    session: Session | None = Depends(get_session),
) -> PlaylistRepository:
    if settings.DB_BACKEND == "dynamodb":
        return DynamoDbPlaylistRepository(get_dynamodb_table())

    return SqlModelPlaylistRepository(session)


def get_favourite_repository(
    session: Session | None = Depends(get_session),
) -> FavouriteRepository:
    if settings.DB_BACKEND == "dynamodb":
        return DynamoDbFavouriteRepository(get_dynamodb_table())

    return SqlModelFavouriteRepository(session)

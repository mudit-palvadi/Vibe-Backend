from types import SimpleNamespace

from app.core.config import settings
from app.db.database import get_session
from app.repositories import dependencies
from app.repositories.dynamodb_repositories import (
    DynamoDbFavouriteRepository,
    DynamoDbPlaylistRepository,
    DynamoDbSongRepository,
    DynamoDbUserRepository,
)
from app.repositories.sqlmodel_repositories import (
    SqlModelFavouriteRepository,
    SqlModelPlaylistRepository,
    SqlModelSongRepository,
    SqlModelUserRepository,
)


def test_the_sqlmodel_repositories_are_used_by_default():
    assert isinstance(dependencies.get_user_repository(session=None), SqlModelUserRepository)
    assert isinstance(dependencies.get_song_repository(session=None), SqlModelSongRepository)
    assert isinstance(
        dependencies.get_playlist_repository(session=None), SqlModelPlaylistRepository
    )
    assert isinstance(
        dependencies.get_favourite_repository(session=None), SqlModelFavouriteRepository
    )


def test_the_dynamodb_repositories_are_used_when_the_flag_is_on(monkeypatch):
    monkeypatch.setattr(settings, "DB_BACKEND", "dynamodb")
    monkeypatch.setattr(
        dependencies,
        "get_dynamodb_table",
        lambda: SimpleNamespace(meta=SimpleNamespace(client=None)),
    )

    assert isinstance(dependencies.get_user_repository(), DynamoDbUserRepository)
    assert isinstance(dependencies.get_song_repository(), DynamoDbSongRepository)
    assert isinstance(dependencies.get_playlist_repository(), DynamoDbPlaylistRepository)
    assert isinstance(dependencies.get_favourite_repository(), DynamoDbFavouriteRepository)


def test_the_postgres_session_is_not_opened_when_dynamodb_is_used(monkeypatch):
    monkeypatch.setattr(settings, "DB_BACKEND", "dynamodb")

    session = None
    for value in get_session():
        session = value

    assert session is None

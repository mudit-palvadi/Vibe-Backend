from contracts import Repositories, RepositoryContract
from sqlmodel import Session

from app.repositories.sqlmodel_repositories import (
    SqlModelFavouriteRepository,
    SqlModelPlaylistRepository,
    SqlModelSongRepository,
    SqlModelUserRepository,
)


class TestSqlModelRepositories(RepositoryContract):
    """the contract the sqlmodel repositories have to keep"""

    def make_repositories(self, engine) -> Repositories:
        session = Session(engine)
        return Repositories(
            users=SqlModelUserRepository(session),
            songs=SqlModelSongRepository(session),
            playlists=SqlModelPlaylistRepository(session),
            favourites=SqlModelFavouriteRepository(session),
        )

import uuid
from uuid import UUID

from sqlmodel import Session, or_, select

from app.models.favourite import Favourite
from app.models.playlist import Playlist, PlaylistSongLink
from app.models.song import Song
from app.models.user import User
from app.repositories.errors import (
    DuplicateSongError,
    PlaylistNotFoundError,
    SongNotFoundError,
    UserNotFoundError,
)
from app.repositories.records import (
    FavouriteRecord,
    FavouriteWithSong,
    PlaylistRecord,
    SongRecord,
    UserRecord,
)
from app.repositories.tags import join_tags, parse_tags


def _to_uuid(value: str | UUID) -> UUID | None:
    if isinstance(value, UUID):
        return value

    try:
        return UUID(value)
    except ValueError:
        return None


def _user_record(user: User) -> UserRecord:
    return UserRecord(
        id=str(user.id),
        name=user.name,
        email=user.email,
        google_sub=user.google_sub,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def _song_record(song: Song) -> SongRecord:
    return SongRecord(
        id=song.id,
        song_name=song.song_name,
        artist=song.artist,
        song_url=song.song_url,
        thumbnail_url=song.thumbnail_url,
        tags=song.tags,
    )


def _playlist_record(playlist: Playlist) -> PlaylistRecord:
    return PlaylistRecord(
        id=str(playlist.id),
        user_id=str(playlist.user_id),
        name=playlist.name,
        description=playlist.description,
        thumbnail_url=playlist.thumbnail_url,
        created_at=playlist.created_at,
    )


class SqlModelUserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, user_id: str | UUID) -> UserRecord | None:
        user_uuid = _to_uuid(user_id)
        if not user_uuid:
            return None

        user = self.session.get(User, user_uuid)
        return _user_record(user) if user else None

    def get_by_email(self, email: str) -> UserRecord | None:
        user = self.session.exec(select(User).where(User.email == email)).first()
        return _user_record(user) if user else None

    def get_by_google_sub(self, google_sub: str) -> UserRecord | None:
        user = self.session.exec(select(User).where(User.google_sub == google_sub)).first()
        return _user_record(user) if user else None

    def create(self, *, name: str, email: str, google_sub: str | None = None) -> UserRecord:
        user = User(name=name, email=email, google_sub=google_sub)
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return _user_record(user)

    def set_google_sub(self, user_id: str, google_sub: str) -> UserRecord:
        user = self._get(user_id)
        user.google_sub = google_sub
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return _user_record(user)

    def set_name(self, user_id: str, name: str) -> UserRecord:
        user = self._get(user_id)
        user.name = name
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return _user_record(user)

    def _get(self, user_id: str) -> User:
        user_uuid = _to_uuid(user_id)
        user = self.session.get(User, user_uuid) if user_uuid else None
        if not user:
            raise UserNotFoundError(f"no user with the id {user_id}")
        return user


class SqlModelSongRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        *,
        song_name: str,
        artist: str,
        song_url: str,
        thumbnail_url: str,
        tags: str,
        song_id: str | None = None,
    ) -> SongRecord:
        song = Song(
            id=song_id or str(uuid.uuid4()),
            song_name=song_name,
            artist=artist,
            song_url=song_url,
            thumbnail_url=thumbnail_url,
            tags=join_tags(parse_tags(tags)),
        )
        self.session.add(song)
        self.session.commit()
        self.session.refresh(song)
        return _song_record(song)

    def get(self, song_id: str) -> SongRecord | None:
        song = self.session.get(Song, song_id)
        return _song_record(song) if song else None

    def list_all(self) -> list[SongRecord]:
        songs = self.session.exec(select(Song).order_by(Song.song_name)).all()
        return [_song_record(song) for song in songs]

    def search(self, query: str) -> list[SongRecord]:
        # a tag matches when it starts with the query, the same way the
        # dynamodb implementation does it
        patterns = [
            f"{query}%",
            f"%,{query},%",
            f"%,{query}",
        ]
        conditions = [Song.song_name.ilike(patterns[0]), Song.artist.ilike(patterns[0])]
        conditions.extend(Song.tags.ilike(pattern) for pattern in patterns)

        songs = (
            self.session.exec(select(Song).where(or_(*conditions)).order_by(Song.song_name)).all()
        )
        return [_song_record(song) for song in songs]


class SqlModelPlaylistRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        *,
        user_id: str,
        name: str,
        description: str | None = None,
        thumbnail_url: str | None = None,
    ) -> PlaylistRecord:
        user_uuid = _to_uuid(user_id)
        if not user_uuid:
            raise UserNotFoundError(f"no user with the id {user_id}")

        playlist = Playlist(
            user_id=user_uuid,
            name=name,
            description=description,
            thumbnail_url=thumbnail_url,
        )
        self.session.add(playlist)
        self.session.commit()
        self.session.refresh(playlist)
        return _playlist_record(playlist)

    def get(self, playlist_id: str) -> PlaylistRecord | None:
        playlist_uuid = _to_uuid(playlist_id)
        playlist = self.session.get(Playlist, playlist_uuid) if playlist_uuid else None
        return _playlist_record(playlist) if playlist else None

    def list_for_user(self, user_id: str) -> list[PlaylistRecord]:
        user_uuid = _to_uuid(user_id)
        if not user_uuid:
            return []

        playlists = self.session.exec(
            select(Playlist).where(Playlist.user_id == user_uuid).order_by(Playlist.created_at)
        ).all()
        return [_playlist_record(playlist) for playlist in playlists]

    def list_songs(self, playlist_id: str) -> list[SongRecord]:
        links = self.session.exec(
            select(PlaylistSongLink)
            .where(PlaylistSongLink.playlist_id == _to_uuid(playlist_id))
            .order_by(PlaylistSongLink.added_at, PlaylistSongLink.id)
        ).all()

        songs = []
        for link in links:
            song = self.session.get(Song, link.song_id)
            if song:
                songs.append(_song_record(song))
        return songs

    def add_song(self, *, playlist_id: str, song_id: str) -> None:
        playlist_uuid = _to_uuid(playlist_id)
        if not playlist_uuid or not self.session.get(Playlist, playlist_uuid):
            raise PlaylistNotFoundError(f"no playlist with the id {playlist_id}")

        if not self.session.get(Song, song_id):
            raise SongNotFoundError(f"no song with the id {song_id}")

        existing = self.session.exec(
            select(PlaylistSongLink).where(
                PlaylistSongLink.playlist_id == playlist_uuid,
                PlaylistSongLink.song_id == song_id,
            )
        ).first()

        if existing:
            raise DuplicateSongError(f"the song {song_id} is already in the playlist {playlist_id}")

        self.session.add(PlaylistSongLink(playlist_id=playlist_uuid, song_id=song_id))
        self.session.commit()

    def remove_song(self, *, playlist_id: str, song_id: str) -> bool:
        playlist_uuid = _to_uuid(playlist_id)
        if not playlist_uuid:
            return False

        link = self.session.exec(
            select(PlaylistSongLink).where(
                PlaylistSongLink.playlist_id == playlist_uuid,
                PlaylistSongLink.song_id == song_id,
            )
        ).first()

        if not link:
            return False

        self.session.delete(link)
        self.session.commit()
        return True

    def delete(self, playlist_id: str) -> None:
        playlist_uuid = _to_uuid(playlist_id)
        playlist = self.session.get(Playlist, playlist_uuid) if playlist_uuid else None
        if not playlist:
            raise PlaylistNotFoundError(f"no playlist with the id {playlist_id}")

        self.session.delete(playlist)
        self.session.commit()


class SqlModelFavouriteRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def toggle(self, *, song_id: str, user_id: str) -> bool:
        user_uuid = _to_uuid(user_id)
        if not user_uuid:
            return False

        existing = self.session.exec(
            select(Favourite).where(
                Favourite.song_id == song_id,
                Favourite.user_id == user_uuid,
            )
        ).first()

        if existing:
            self.session.delete(existing)
            self.session.commit()
            return False

        self.session.add(
            Favourite(id=str(uuid.uuid4()), song_id=song_id, user_id=user_uuid),
        )
        self.session.commit()
        return True

    def get(self, *, song_id: str, user_id: str) -> FavouriteRecord | None:
        user_uuid = _to_uuid(user_id)
        if not user_uuid:
            return None

        favourite = self.session.exec(
            select(Favourite).where(
                Favourite.song_id == song_id,
                Favourite.user_id == user_uuid,
            )
        ).first()

        if not favourite:
            return None

        return FavouriteRecord(
            id=favourite.id,
            song_id=favourite.song_id,
            user_id=str(favourite.user_id),
        )

    def list_for_user(self, user_id: str) -> list[FavouriteWithSong]:
        user_uuid = _to_uuid(user_id)
        if not user_uuid:
            return []

        favourites = self.session.exec(
            select(Favourite)
            .where(Favourite.user_id == user_uuid)
            .join(Song, Song.id == Favourite.song_id)
            .order_by(Favourite.song_id)
        ).all()

        results = []
        for favourite in favourites:
            song = self.session.get(Song, favourite.song_id)
            if not song:
                continue
            results.append(
                FavouriteWithSong(
                    id=favourite.id,
                    song_id=favourite.song_id,
                    user_id=str(favourite.user_id),
                    song=_song_record(song),
                )
            )
        return results

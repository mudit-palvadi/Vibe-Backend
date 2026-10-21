from typing import Protocol

from app.repositories.records import (
    FavouriteRecord,
    FavouriteWithSong,
    PlaylistRecord,
    SongRecord,
    UserRecord,
)


class UserRepository(Protocol):
    def get_by_id(self, user_id: str) -> UserRecord | None: ...

    def get_by_email(self, email: str) -> UserRecord | None: ...

    def get_by_google_sub(self, google_sub: str) -> UserRecord | None: ...

    def create(
        self,
        *,
        name: str,
        email: str,
        google_sub: str | None = None,
        user_id: str | None = None,
    ) -> UserRecord: ...

    def set_google_sub(self, user_id: str, google_sub: str) -> UserRecord: ...

    def set_name(self, user_id: str, name: str) -> UserRecord: ...


class SongRepository(Protocol):
    def create(
        self,
        *,
        song_name: str,
        artist: str,
        song_url: str,
        thumbnail_url: str,
        tags: str,
        song_id: str | None = None,
    ) -> SongRecord: ...

    def get(self, song_id: str) -> SongRecord | None: ...

    def list_all(self) -> list[SongRecord]: ...

    def search(self, query: str) -> list[SongRecord]: ...


class PlaylistRepository(Protocol):
    def create(
        self,
        *,
        user_id: str,
        name: str,
        description: str | None = None,
        thumbnail_url: str | None = None,
        playlist_id: str | None = None,
    ) -> PlaylistRecord: ...

    def get(self, playlist_id: str) -> PlaylistRecord | None: ...

    def list_for_user(self, user_id: str) -> list[PlaylistRecord]: ...

    def list_songs(self, playlist_id: str) -> list[SongRecord]: ...

    def add_song(self, *, playlist_id: str, song_id: str) -> None: ...

    def remove_song(self, *, playlist_id: str, song_id: str) -> bool: ...

    def delete(self, playlist_id: str) -> None: ...


class FavouriteRepository(Protocol):
    def toggle(self, *, song_id: str, user_id: str) -> bool: ...

    def get(self, *, song_id: str, user_id: str) -> FavouriteRecord | None: ...

    def list_for_user(self, user_id: str) -> list[FavouriteWithSong]: ...

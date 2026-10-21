"""the behaviour every repository implementation has to have

the same suite runs against the sqlmodel repositories and, later on, against
the dynamodb ones
"""

from dataclasses import dataclass

import pytest

from app.repositories.errors import DuplicateSongError
from app.repositories.protocols import (
    FavouriteRepository,
    PlaylistRepository,
    SongRepository,
    UserRepository,
)


@dataclass
class Repositories:
    users: UserRepository
    songs: SongRepository
    playlists: PlaylistRepository
    favourites: FavouriteRepository


class RepositoryContract:
    """the contract the repository implementations have to keep"""

    def make_repositories(self, engine) -> Repositories:
        raise NotImplementedError

    @pytest.fixture()
    def repos(self, db):
        return self.make_repositories(db)

    def make_user(self, repos, name="Test User", email="test@example.com", google_sub=None):
        return repos.users.create(name=name, email=email, google_sub=google_sub)

    def make_song(
        self,
        repos,
        song_name="Test Song",
        artist="Test Artist",
        tags="pop,test",
        song_id=None,
    ):
        return repos.songs.create(
            song_id=song_id,
            song_name=song_name,
            artist=artist,
            song_url="https://example.com/song.mp3",
            thumbnail_url="https://example.com/thumb.jpg",
            tags=tags,
        )

    def make_playlist(self, repos, user, name="My Playlist"):
        return repos.playlists.create(user_id=user.id, name=name)

    # the user repository

    def test_a_new_user_is_found_by_the_id(self, repos):
        created = self.make_user(repos)

        found = repos.users.get_by_id(created.id)

        assert found is not None
        assert found.id == created.id
        assert found.name == "Test User"
        assert found.email == "test@example.com"

    def test_a_user_is_found_by_the_email(self, repos):
        created = self.make_user(repos)

        found = repos.users.get_by_email("test@example.com")

        assert found is not None
        assert found.id == created.id

    def test_a_user_is_found_by_the_google_id(self, repos):
        created = self.make_user(repos, google_sub="google-sub-1")

        found = repos.users.get_by_google_sub("google-sub-1")

        assert found is not None
        assert found.id == created.id

    def test_a_user_that_does_not_exist_is_not_found(self, repos):
        assert repos.users.get_by_id("nobody") is None
        assert repos.users.get_by_email("nobody@example.com") is None
        assert repos.users.get_by_google_sub("no-google-sub-nobody-has") is None

    def test_the_google_id_can_be_set_on_a_user(self, repos):
        created = self.make_user(repos)

        updated = repos.users.set_google_sub(created.id, "google-sub-1")

        assert updated.google_sub == "google-sub-1"
        assert repos.users.get_by_google_sub("google-sub-1").id == created.id

    def test_the_name_of_a_user_can_be_changed(self, repos):
        created = self.make_user(repos)

        updated = repos.users.set_name(created.id, "New Name")

        assert updated.name == "New Name"

    # the song repository

    def test_a_new_song_is_found_by_the_id(self, repos):
        created = self.make_song(repos)

        found = repos.songs.get(created.id)

        assert found is not None
        assert found.song_name == "Test Song"
        assert found.artist == "Test Artist"
        assert found.song_url == "https://example.com/song.mp3"
        assert found.thumbnail_url == "https://example.com/thumb.jpg"

    def test_a_song_that_does_not_exist_is_not_found(self, repos):
        assert repos.songs.get("no-such-song") is None

    def test_the_tags_of_a_song_are_cleaned_up(self, repos):
        created = self.make_song(repos, tags=" pop , rock , ")

        assert created.tags == "pop,rock"

    def test_all_the_songs_are_listed_in_alphabetical_order(self, repos):
        self.make_song(repos, song_name="Zebra Song")
        self.make_song(repos, song_name="Apple Song")
        self.make_song(repos, song_name="Mango Song")

        songs = repos.songs.list_all()

        assert [song.song_name for song in songs] == ["Apple Song", "Mango Song", "Zebra Song"]

    def test_the_songs_are_searched_by_the_start_of_the_name(self, repos):
        self.make_song(repos, song_name="Blue Monday", artist="New Order", tags="electronic")
        self.make_song(repos, song_name="Test Song", artist="Test Artist", tags="pop")

        songs = repos.songs.search("blue")

        assert [song.song_name for song in songs] == ["Blue Monday"]

    def test_the_songs_are_searched_by_the_start_of_the_artist(self, repos):
        self.make_song(repos, song_name="Blue Monday", artist="New Order", tags="electronic")
        self.make_song(repos, song_name="Test Song", artist="Test Artist", tags="pop")

        songs = repos.songs.search("new")

        assert [song.song_name for song in songs] == ["Blue Monday"]

    def test_the_songs_are_searched_by_the_start_of_a_tag(self, repos):
        self.make_song(repos, song_name="Blue Monday", artist="New Order", tags="pop,electronic")
        self.make_song(repos, song_name="Test Song", artist="Test Artist", tags="pop,test")
        self.make_song(repos, song_name="Rock Song", artist="Someone Else", tags="rock")

        songs = repos.songs.search("pop")

        assert [song.song_name for song in songs] == ["Blue Monday", "Test Song"]

    def test_the_search_does_not_match_the_middle_of_a_word(self, repos):
        self.make_song(repos, song_name="Blue Monday", artist="New Order", tags="electronic")

        assert repos.songs.search("onday") == []
        assert repos.songs.search("lectronic") == []

    def test_the_search_finds_nothing_for_a_query_without_a_match(self, repos):
        self.make_song(repos, song_name="Blue Monday", artist="New Order", tags="electronic")

        assert repos.songs.search("nothing-like-this") == []

    # the playlist repository

    def test_a_new_playlist_is_found_by_the_id(self, repos):
        user = self.make_user(repos)

        created = self.make_playlist(repos, user)

        found = repos.playlists.get(created.id)

        assert found is not None
        assert found.name == "My Playlist"
        assert found.user_id == user.id

    def test_a_playlist_that_does_not_exist_is_not_found(self, repos):
        assert repos.playlists.get("no-such-playlist") is None

    def test_the_playlists_are_listed_for_the_user(self, repos):
        user = self.make_user(repos)
        other_user = self.make_user(repos, email="other@example.com")
        self.make_playlist(repos, user, name="Mine")
        self.make_playlist(repos, user, name="Mine Too")
        self.make_playlist(repos, other_user, name="Not Mine")

        playlists = repos.playlists.list_for_user(user.id)

        assert {playlist.name for playlist in playlists} == {"Mine", "Mine Too"}

    def test_a_song_can_be_added_to_a_playlist(self, repos):
        user = self.make_user(repos)
        playlist = self.make_playlist(repos, user)
        song = self.make_song(repos)

        repos.playlists.add_song(playlist_id=playlist.id, song_id=song.id)

        assert [item.id for item in repos.playlists.list_songs(playlist.id)] == [song.id]

    def test_the_same_song_cannot_be_added_twice(self, repos):
        user = self.make_user(repos)
        playlist = self.make_playlist(repos, user)
        song = self.make_song(repos)
        repos.playlists.add_song(playlist_id=playlist.id, song_id=song.id)

        with pytest.raises(DuplicateSongError):
            repos.playlists.add_song(playlist_id=playlist.id, song_id=song.id)

    def test_a_song_can_be_removed_from_a_playlist(self, repos):
        user = self.make_user(repos)
        playlist = self.make_playlist(repos, user)
        song = self.make_song(repos)
        repos.playlists.add_song(playlist_id=playlist.id, song_id=song.id)

        removed = repos.playlists.remove_song(playlist_id=playlist.id, song_id=song.id)

        assert removed is True
        assert repos.playlists.list_songs(playlist.id) == []

    def test_removing_a_song_that_is_not_in_the_playlist_says_so(self, repos):
        user = self.make_user(repos)
        playlist = self.make_playlist(repos, user)
        song = self.make_song(repos)

        assert repos.playlists.remove_song(playlist_id=playlist.id, song_id=song.id) is False

    def test_a_playlist_can_be_deleted(self, repos):
        user = self.make_user(repos)
        playlist = self.make_playlist(repos, user)

        repos.playlists.delete(playlist.id)

        assert repos.playlists.get(playlist.id) is None

    # the favourite repository

    def test_a_song_can_be_favourited_and_unfavourited(self, repos):
        user = self.make_user(repos)
        song = self.make_song(repos)

        assert repos.favourites.toggle(song_id=song.id, user_id=user.id) is True
        assert repos.favourites.toggle(song_id=song.id, user_id=user.id) is False

    def test_a_favourite_can_be_found(self, repos):
        user = self.make_user(repos)
        song = self.make_song(repos)
        repos.favourites.toggle(song_id=song.id, user_id=user.id)

        favourite = repos.favourites.get(song_id=song.id, user_id=user.id)

        assert favourite is not None
        assert favourite.song_id == song.id
        assert favourite.user_id == user.id

    def test_a_favourite_that_does_not_exist_is_not_found(self, repos):
        user = self.make_user(repos)
        song = self.make_song(repos)

        assert repos.favourites.get(song_id=song.id, user_id=user.id) is None

    def test_the_favourites_are_listed_with_their_song(self, repos):
        user = self.make_user(repos)
        song = self.make_song(repos)
        repos.favourites.toggle(song_id=song.id, user_id=user.id)

        favourites = repos.favourites.list_for_user(user.id)

        assert len(favourites) == 1
        assert favourites[0].song_id == song.id
        assert favourites[0].song.song_name == "Test Song"

    def test_the_favourites_of_another_user_are_not_listed(self, repos):
        user = self.make_user(repos)
        other_user = self.make_user(repos, email="other@example.com")
        song = self.make_song(repos)
        repos.favourites.toggle(song_id=song.id, user_id=other_user.id)

        assert repos.favourites.list_for_user(user.id) == []

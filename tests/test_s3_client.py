import pytest

from app.core.config import settings
from app.storage import s3


def test_the_temp_key_keeps_the_extension():
    assert s3.build_temp_key("abc", "My Song.MP3", "audio") == "tmp/abc/audio.mp3"
    assert s3.build_temp_key("abc", "cover.png", "thumbnail") == "tmp/abc/thumbnail.png"


def test_the_final_key_moves_the_file_to_the_songs_folder():
    assert s3.build_final_key("tmp/abc/audio.mp3") == "songs/abc/audio.mp3"


def test_only_the_own_song_keys_are_temp_keys():
    assert s3.is_temp_key("tmp/abc/audio.mp3", "abc")
    assert not s3.is_temp_key("tmp/other/audio.mp3", "abc")
    assert not s3.is_temp_key("songs/abc/audio.mp3", "abc")


def test_the_media_url_uses_the_media_base_url(monkeypatch):
    monkeypatch.setattr(settings, "MEDIA_BASE_URL", "https://media.test/")

    assert s3.media_url("songs/abc/audio.mp3") == "https://media.test/songs/abc/audio.mp3"


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("song.mp3", "audio/mpeg"),
        ("cover.jpg", "image/jpeg"),
        ("cover.png", "image/png"),
        ("song.unknown", "application/octet-stream"),
    ],
)
def test_the_content_type_is_guessed_from_the_name(filename, expected):
    assert s3.guess_content_type(filename) == expected

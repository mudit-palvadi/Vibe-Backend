from sqlmodel import select

from app.models.song import Song


def test_upload_song(client, session, auth_headers, current_user, monkeypatch):
    calls = []

    def fake_upload(file, resource_type="auto", folder=None, **kwargs):
        calls.append({"resource_type": resource_type, "folder": folder})
        return {"url": f"https://res.cloudinary.com/test/{resource_type}/{folder}"}

    monkeypatch.setattr("app.routes.song_routes.cloudinary.uploader.upload", fake_upload)

    response = client.post(
        "/song/upload",
        headers=auth_headers,
        data={"artist": "Test Artist", "song_name": "Test Song", "tags": "pop"},
        files={
            "song_audio": ("song.mp3", b"audio-bytes", "audio/mpeg"),
            "thumbnail": ("thumb.jpg", b"image-bytes", "image/jpeg"),
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["message"] == "Song uploaded successfully"
    assert body["song"]["song_name"] == "Test Song"
    assert body["song"]["artist"] == "Test Artist"
    assert body["song"]["tags"] == "pop"

    song_id = body["song"]["id"]
    assert calls[0]["folder"] == f"songs/{song_id}"
    assert calls[1]["folder"] == f"songs/{song_id}"
    assert calls[0]["resource_type"] == "auto"
    assert calls[1]["resource_type"] == "image"

    song = session.exec(select(Song).where(Song.id == song_id)).one()
    assert song.song_url == body["song"]["song_url"]


def test_fetch_songs(client, session, auth_headers, current_user):
    for index in range(2):
        session.add(
            Song(
                id=f"song-{index}",
                song_name=f"Song {index}",
                artist="Test Artist",
                song_url="https://example.com/song.mp3",
                thumbnail_url="https://example.com/thumb.jpg",
                tags="pop",
            )
        )
    session.commit()

    response = client.get("/song/list", headers=auth_headers)

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_search_songs_by_name(client, auth_headers, current_user, song):
    response = client.get("/song/search", params={"q": "Test Song"}, headers=auth_headers)

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == ["song-1"]


def test_search_songs_by_artist(client, auth_headers, current_user, song):
    response = client.get("/song/search", params={"q": "Test Artist"}, headers=auth_headers)

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_search_songs_by_tags(client, auth_headers, current_user, song):
    response = client.get("/song/search", params={"q": "pop"}, headers=auth_headers)

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_search_songs_without_a_match(client, auth_headers, current_user, song):
    response = client.get("/song/search", params={"q": "nothing"}, headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == []


def test_song_routes_need_a_token(client, song):
    response = client.get("/song/list")

    assert response.status_code == 401

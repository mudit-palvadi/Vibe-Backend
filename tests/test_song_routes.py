from app.models.song import Song


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

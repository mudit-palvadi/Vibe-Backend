def test_upload_complete_creates_the_song(client, auth_headers, current_user, monkeypatch):
    song_id = "song-123"
    monkeypatch.setattr("app.routes.song_routes.object_exists", lambda key: True)
    monkeypatch.setattr(
        "app.routes.song_routes.copy_to_final_place",
        lambda key: key.replace("tmp/", "songs/", 1),
    )
    monkeypatch.setattr(
        "app.routes.song_routes.media_url",
        lambda key: f"https://media.test/{key}",
    )

    response = client.post(
        "/song/upload-complete",
        json={
            "song_id": song_id,
            "song_name": "Test Song",
            "artist": "Test Artist",
            "tags": "pop",
            "audio_key": f"tmp/{song_id}/audio.mp3",
            "thumbnail_key": f"tmp/{song_id}/thumbnail.jpg",
        },
        headers=auth_headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["message"] == "Song uploaded successfully"
    assert body["song"]["id"] == song_id
    assert body["song"]["song_name"] == "Test Song"
    assert body["song"]["song_url"] == f"https://media.test/songs/{song_id}/audio.mp3"
    assert body["song"]["thumbnail_url"] == f"https://media.test/songs/{song_id}/thumbnail.jpg"


def test_upload_complete_rejects_the_keys_of_another_song(
    client, auth_headers, current_user, monkeypatch
):
    monkeypatch.setattr("app.routes.song_routes.object_exists", lambda key: True)

    response = client.post(
        "/song/upload-complete",
        json={
            "song_id": "song-123",
            "song_name": "Test Song",
            "artist": "Test Artist",
            "audio_key": "tmp/other-song/audio.mp3",
            "thumbnail_key": "tmp/other-song/thumbnail.jpg",
        },
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "The upload keys do not belong to this song"


def test_upload_complete_needs_the_files_in_the_bucket(
    client, auth_headers, current_user, monkeypatch
):
    monkeypatch.setattr("app.routes.song_routes.object_exists", lambda key: False)

    response = client.post(
        "/song/upload-complete",
        json={
            "song_id": "song-123",
            "song_name": "Test Song",
            "artist": "Test Artist",
            "audio_key": "tmp/song-123/audio.mp3",
            "thumbnail_key": "tmp/song-123/thumbnail.jpg",
        },
        headers=auth_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "The files are not in the bucket yet"

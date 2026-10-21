def test_upload_init_gives_two_links(client, auth_headers, current_user, monkeypatch):
    monkeypatch.setattr(
        "app.routes.song_routes.create_upload_url",
        lambda key, content_type: {
            "key": key,
            "url": f"https://s3.test/{key}",
            "headers": {"Content-Type": content_type},
        },
    )

    response = client.post(
        "/song/upload-init",
        json={
            "song_name": "Test Song",
            "artist": "Test Artist",
            "tags": "pop",
            "audio_filename": "song.mp3",
            "thumbnail_filename": "cover.jpg",
        },
        headers=auth_headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["audio"]["key"] == f"tmp/{body['song_id']}/audio.mp3"
    assert body["thumbnail"]["key"] == f"tmp/{body['song_id']}/thumbnail.jpg"
    assert body["audio"]["headers"]["Content-Type"] == "audio/mpeg"
    assert body["thumbnail"]["headers"]["Content-Type"] == "image/jpeg"
    assert body["expires_in"] == 900

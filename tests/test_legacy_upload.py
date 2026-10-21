from app.core.config import settings


def test_the_old_upload_endpoint_can_be_turned_off(client, auth_headers, current_user, monkeypatch):
    monkeypatch.setattr(settings, "LEGACY_UPLOAD_ENABLED", False)

    response = client.post(
        "/song/upload",
        files={
            "song_audio": ("song.mp3", b"audio", "audio/mpeg"),
            "thumbnail": ("cover.jpg", b"image", "image/jpeg"),
        },
        data={"artist": "Test Artist", "song_name": "Test Song", "tags": "pop"},
        headers=auth_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "The old upload endpoint is turned off"

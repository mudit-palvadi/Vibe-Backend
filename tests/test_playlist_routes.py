from sqlmodel import select

from app.models.playlist import Playlist, PlaylistSongLink


def test_create_playlist(client, session, auth_headers, current_user):
    response = client.post(
        "/playlist/create",
        headers=auth_headers,
        json={"name": "My Playlist", "description": "a description"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "My Playlist"
    assert body["description"] == "a description"
    assert body["user_id"] == str(current_user.id)

    playlist = session.exec(select(Playlist)).one()
    assert str(playlist.id) == body["id"]


def test_list_playlists(client, session, auth_headers, current_user):
    session.add(Playlist(user_id=current_user.id, name="My Playlist"))
    session.add(Playlist(user_id=current_user.id, name="Another Playlist"))
    session.commit()

    response = client.get("/playlist/list", headers=auth_headers)

    assert response.status_code == 200
    assert {item["name"] for item in response.json()} == {"My Playlist", "Another Playlist"}


def test_playlist_details_include_the_songs(client, session, auth_headers, current_user, song):
    playlist = Playlist(user_id=current_user.id, name="My Playlist")
    session.add(playlist)
    session.commit()
    session.add(PlaylistSongLink(playlist_id=playlist.id, song_id=song.id))
    session.commit()

    response = client.get(f"/playlist/{playlist.id}", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "My Playlist"
    assert [item["id"] for item in body["songs"]] == ["song-1"]


def test_playlist_details_for_a_missing_playlist(client, auth_headers, current_user):
    response = client.get("/playlist/22222222-2222-4222-8222-222222222222", headers=auth_headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "Playlist not found"


def test_add_song_to_playlist(client, session, auth_headers, current_user, song):
    playlist = Playlist(user_id=current_user.id, name="My Playlist")
    session.add(playlist)
    session.commit()

    response = client.post(
        "/playlist/add-song",
        headers=auth_headers,
        json={"playlist_id": str(playlist.id), "song_id": song.id},
    )

    assert response.status_code == 201
    assert response.json()["message"] == "Song added to playlist successfully"

    link = session.exec(select(PlaylistSongLink)).one()
    assert link.song_id == song.id


def test_add_the_same_song_twice(client, session, auth_headers, current_user, song):
    playlist = Playlist(user_id=current_user.id, name="My Playlist")
    session.add(playlist)
    session.commit()
    session.add(PlaylistSongLink(playlist_id=playlist.id, song_id=song.id))
    session.commit()

    response = client.post(
        "/playlist/add-song",
        headers=auth_headers,
        json={"playlist_id": str(playlist.id), "song_id": song.id},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Song is already in the playlist"


def test_add_song_to_a_missing_playlist(client, auth_headers, current_user, song):
    response = client.post(
        "/playlist/add-song",
        headers=auth_headers,
        json={
            "playlist_id": "22222222-2222-4222-8222-222222222222",
            "song_id": song.id,
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Playlist not found or access denied"


def test_add_a_missing_song_to_a_playlist(client, session, auth_headers, current_user):
    playlist = Playlist(user_id=current_user.id, name="My Playlist")
    session.add(playlist)
    session.commit()

    response = client.post(
        "/playlist/add-song",
        headers=auth_headers,
        json={"playlist_id": str(playlist.id), "song_id": "does-not-exist"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Song not found"


def test_remove_song_from_playlist(client, session, auth_headers, current_user, song):
    playlist = Playlist(user_id=current_user.id, name="My Playlist")
    session.add(playlist)
    session.commit()
    session.add(PlaylistSongLink(playlist_id=playlist.id, song_id=song.id))
    session.commit()

    response = client.request(
        "DELETE",
        "/playlist/remove-song",
        headers=auth_headers,
        json={"playlist_id": str(playlist.id), "song_id": song.id},
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Song removed from playlist successfully"
    assert session.exec(select(PlaylistSongLink)).all() == []


def test_delete_playlist(client, session, auth_headers, current_user):
    playlist = Playlist(user_id=current_user.id, name="My Playlist")
    session.add(playlist)
    session.commit()

    response = client.delete(f"/playlist/{playlist.id}", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["message"] == "Playlist deleted successfully"
    assert session.exec(select(Playlist)).all() == []


def test_delete_someone_elses_playlist(client, session, auth_headers, current_user):
    from uuid import uuid4

    from app.models.user import User

    other = User(id=uuid4(), name="Other User", email="other@example.com")
    session.add(other)
    session.commit()
    playlist = Playlist(user_id=other.id, name="Not Mine")
    session.add(playlist)
    session.commit()

    response = client.delete(f"/playlist/{playlist.id}", headers=auth_headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "Playlist not found or access denied"

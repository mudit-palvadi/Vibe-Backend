from sqlmodel import select

from app.models.favourite import Favourite


def test_favourite_toggle_adds_the_song(client, session, auth_headers, current_user, song):
    response = client.post(
        "/song/favourite",
        headers=auth_headers,
        json={"song_id": song.id},
    )

    assert response.status_code == 201
    assert response.json() == {"message": True}

    favourite = session.exec(select(Favourite)).one()
    assert favourite.song_id == song.id
    assert favourite.user_id == current_user.id


def test_favourite_toggle_removes_the_song(client, session, auth_headers, current_user, song):
    client.post("/song/favourite", headers=auth_headers, json={"song_id": song.id})

    response = client.post(
        "/song/favourite",
        headers=auth_headers,
        json={"song_id": song.id},
    )

    assert response.status_code == 201
    assert response.json() == {"message": False}
    assert session.exec(select(Favourite)).all() == []


def test_favourite_toggle_needs_a_token(client, song):
    response = client.post("/song/favourite", json={"song_id": song.id})

    assert response.status_code == 401


def test_list_favourites(client, session, auth_headers, current_user, song):
    client.post("/song/favourite", headers=auth_headers, json={"song_id": song.id})

    response = client.get("/song/list-favourites", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["song_id"] == song.id
    assert body[0]["song"]["song_name"] == "Test Song"

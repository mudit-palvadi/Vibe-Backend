def test_home_endpoint(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "Vibe backend running"}


def test_openapi_schema_is_generated(client):
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/song/list" in response.json()["paths"]


def test_tables_are_created(db):
    from sqlmodel import SQLModel

    assert set(SQLModel.metadata.tables) == {
        "favourites",
        "playlist_songs",
        "playlists",
        "songs",
        "users",
    }

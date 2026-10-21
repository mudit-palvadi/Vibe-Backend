"""moves the songs, the playlists, and the favourites to dynamodb

the media map file of the copy_media_to_s3 script is used to know the new
urls of the song files

run it once with the database url of the old postgres database:
    python scripts/migrate_content_to_dynamodb.py
"""

import json
import os
import sys

import boto3
import psycopg2
from psycopg2.extras import RealDictCursor

# the script only needs the database url, so the other settings are not required
os.environ.setdefault("GOOGLE_CLIENT_ID", "not-needed-for-this-script")
os.environ.setdefault("SESSION_SECRET", "not-needed-for-this-script-but-long-enough")

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from app.core.config import settings  # noqa: E402
from app.repositories.dynamodb_repositories import (  # noqa: E402
    DynamoDbFavouriteRepository,
    DynamoDbPlaylistRepository,
    DynamoDbSongRepository,
)

MEDIA_MAP_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "media_map.json")


def get_connection():
    # psycopg2 does not know the sqlalchemy driver suffix
    url = settings.DATABASE_URL.replace("postgresql+psycopg2://", "postgresql://")
    return psycopg2.connect(url)


def get_rows(connection, query: str) -> list[dict]:
    with connection.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(query)
        return cursor.fetchall()


def get_media_map() -> dict:
    if not os.path.exists(MEDIA_MAP_PATH):
        print("there is no media map file, the old urls are kept")
        return {}

    with open(MEDIA_MAP_PATH, encoding="utf-8") as file:
        return json.load(file)


def get_table():
    resource = boto3.resource("dynamodb", region_name=settings.AWS_REGION)
    return resource.Table(settings.DYNAMODB_TABLE_NAME)


def main() -> None:
    connection = get_connection()

    try:
        songs = get_rows(
            connection,
            "select id, song_name, artist, song_url, thumbnail_url, tags from songs",
        )
        playlists = get_rows(
            connection,
            "select id, user_id, name, description, thumbnail_url from playlists",
        )
        playlist_songs = get_rows(
            connection,
            "select playlist_id, song_id from playlist_songs",
        )
        favourites = get_rows(connection, "select song_id, user_id from favourites")
    finally:
        connection.close()

    media_map = get_media_map()
    table = get_table()

    songs_repository = DynamoDbSongRepository(table)
    for song in songs:
        media = media_map.get(song["id"], {})
        songs_repository.create(
            song_id=song["id"],
            song_name=song["song_name"],
            artist=song["artist"],
            song_url=media.get("song_url", song["song_url"]),
            thumbnail_url=media.get("thumbnail_url", song["thumbnail_url"]),
            tags=song["tags"] or "",
        )
    print(f"moved {len(songs)} songs to dynamodb")

    playlists_repository = DynamoDbPlaylistRepository(table)
    for playlist in playlists:
        playlists_repository.create(
            playlist_id=str(playlist["id"]),
            user_id=str(playlist["user_id"]),
            name=playlist["name"],
            description=playlist["description"],
            thumbnail_url=playlist["thumbnail_url"],
        )
    print(f"moved {len(playlists)} playlists to dynamodb")

    for link in playlist_songs:
        playlists_repository.add_song(
            playlist_id=str(link["playlist_id"]),
            song_id=link["song_id"],
        )
    print(f"moved {len(playlist_songs)} songs to the playlists")

    favourites_repository = DynamoDbFavouriteRepository(table)
    for favourite in favourites:
        favourites_repository.toggle(
            song_id=favourite["song_id"],
            user_id=str(favourite["user_id"]),
        )
    print(f"moved {len(favourites)} favourites to dynamodb")


if __name__ == "__main__":
    main()

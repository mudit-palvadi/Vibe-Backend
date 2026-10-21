"""copies the song files from cloudinary to the s3 bucket

it writes a media map file, the script that moves the songs to dynamodb
reads it to know the new urls of the files

run it once:
    python scripts/copy_media_to_s3.py
"""

import json
import os
import sys
import time
import urllib.request
from io import BytesIO
from urllib.parse import urlparse

import boto3
import psycopg2
from psycopg2.extras import RealDictCursor

# the script only needs the database url, so the other settings are not required
os.environ.setdefault("GOOGLE_CLIENT_ID", "not-needed-for-this-script")
os.environ.setdefault("SESSION_SECRET", "not-needed-for-this-script-but-long-enough")

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from app.core.config import settings  # noqa: E402
from app.storage.s3 import FINAL_PREFIX, guess_content_type, media_url  # noqa: E402

MEDIA_MAP_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "media_map.json")


def get_connection():
    # psycopg2 does not know the sqlalchemy driver suffix
    url = settings.DATABASE_URL.replace("postgresql+psycopg2://", "postgresql://")
    return psycopg2.connect(url)


def get_songs(connection) -> list[dict]:
    with connection.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute("select id, song_url, thumbnail_url from songs order by song_name")
        return cursor.fetchall()


def get_extension(url: str) -> str:
    return os.path.splitext(urlparse(url).path)[1].lower()


DOWNLOAD_TIMEOUT = 600
DOWNLOAD_ATTEMPTS = 4


def download(url: str) -> bytes:
    """the files are big and the connection is slow, so it tries a few times"""
    last_error = None

    for attempt in range(1, DOWNLOAD_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(url, timeout=DOWNLOAD_TIMEOUT) as response:
                return response.read()
        except (TimeoutError, OSError) as error:
            last_error = error
            print(f"the download of {url} failed ({error}), try {attempt} of {DOWNLOAD_ATTEMPTS}")
            time.sleep(5)

    raise RuntimeError(f"the file could not be downloaded: {url}") from last_error


def upload(client, bucket: str, key: str, url: str) -> None:
    body = download(url)
    client.upload_fileobj(
        BytesIO(body),
        bucket,
        key,
        ExtraArgs={"ContentType": guess_content_type(key)},
    )


def already_there(client, bucket: str, key: str) -> bool:
    """a file that is already in the bucket is not downloaded again"""
    try:
        client.head_object(Bucket=bucket, Key=key)
        return True
    except client.exceptions.ClientError:
        return False


def main() -> None:
    connection = get_connection()

    try:
        songs = get_songs(connection)
    finally:
        connection.close()

    client = boto3.client("s3", region_name=settings.S3_REGION)
    media_map = {}

    if os.path.exists(MEDIA_MAP_PATH):
        with open(MEDIA_MAP_PATH, encoding="utf-8") as file:
            media_map = json.load(file)

    for song in songs:
        song_id = song["id"]
        audio_key = f"{FINAL_PREFIX}/{song_id}/audio{get_extension(song['song_url'])}"
        thumbnail_key = f"{FINAL_PREFIX}/{song_id}/thumbnail{get_extension(song['thumbnail_url'])}"

        for key, url in ((audio_key, song["song_url"]), (thumbnail_key, song["thumbnail_url"])):
            if already_there(client, settings.S3_BUCKET, key):
                print(f"the file {key} is already in the bucket")
                continue

            upload(client, settings.S3_BUCKET, key, url)

        media_map[song_id] = {
            "song_url": media_url(audio_key),
            "thumbnail_url": media_url(thumbnail_key),
        }

        # the map is written after every song, so a broken connection does not lose the work
        with open(MEDIA_MAP_PATH, "w", encoding="utf-8") as file:
            json.dump(media_map, file, indent=2)

        print(f"copied the files of the song {song_id}")

    with open(MEDIA_MAP_PATH, "w", encoding="utf-8") as file:
        json.dump(media_map, file, indent=2)

    print(f"copied the files of {len(songs)} songs and wrote {MEDIA_MAP_PATH}")


if __name__ == "__main__":
    main()

"""copies the song files from cloudinary to the s3 bucket

it writes a media map file, the script that moves the songs to dynamodb
reads it to know the new urls of the files

run it once:
    python scripts/copy_media_to_s3.py
"""

import json
import os
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
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


DOWNLOAD_TIMEOUT = 60
DOWNLOAD_ATTEMPTS = 20
CHUNK_SIZE = 1024 * 1024
READ_SIZE = 64 * 1024


def download(url: str, target: Path) -> None:
    """the files are big and the connection is slow, so the file is fetched in
    small pieces and the part that is already there is kept for the next try"""
    part = target.with_name(target.name + ".part")
    part.parent.mkdir(parents=True, exist_ok=True)
    total = None

    for attempt in range(1, DOWNLOAD_ATTEMPTS + 1):
        try:
            while True:
                have = part.stat().st_size if part.exists() else 0
                if total is not None and have >= total:
                    part.replace(target)
                    return

                request = urllib.request.Request(
                    url,
                    headers={"Range": f"bytes={have}-{have + CHUNK_SIZE - 1}"},
                )
                with urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT) as response:
                    if have and response.status != 206:
                        # the server sent the whole file again, so the part we have is useless
                        part.unlink(missing_ok=True)
                        have = 0

                    # the range of the answer tells how big the whole file is
                    content_range = response.headers.get("Content-Range")
                    if content_range and "/" in content_range:
                        total = int(content_range.split("/")[-1])
                    else:
                        length = response.headers.get("Content-Length")
                        if length:
                            total = int(length) + have

                    with part.open("ab") as handle:
                        while True:
                            chunk = response.read(READ_SIZE)
                            if not chunk:
                                break
                            handle.write(chunk)

                if part.stat().st_size == have:
                    raise OSError("the server did not send any more data")
        except (TimeoutError, OSError) as error:
            print(f"the download of {url} failed ({error}), try {attempt} of {DOWNLOAD_ATTEMPTS}")
            time.sleep(5)
            continue

    raise RuntimeError(f"the file could not be downloaded: {url}")


def upload(client, bucket: str, key: str, url: str) -> None:
    target = Path(tempfile.gettempdir()) / "vibe_media" / key.replace("/", "_")
    download(url, target)
    client.upload_file(
        str(target),
        bucket,
        key,
        ExtraArgs={"ContentType": guess_content_type(key)},
    )
    target.unlink(missing_ok=True)


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

        failed = False

        for key, url in ((audio_key, song["song_url"]), (thumbnail_key, song["thumbnail_url"])):
            if already_there(client, settings.S3_BUCKET, key):
                print(f"the file {key} is already in the bucket")
                continue

            try:
                upload(client, settings.S3_BUCKET, key, url)
            except RuntimeError as error:
                # the song is skipped, the other songs still get copied
                print(f"the song {song_id} was skipped ({error})")
                failed = True
                break

        if failed:
            continue

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

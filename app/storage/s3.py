import mimetypes
import os

from app.core.config import settings

# the files are uploaded to the temp place first, the ones that are never
# finished are removed by the lifecycle rule of the bucket
TEMP_PREFIX = "tmp"
FINAL_PREFIX = "songs"

_client = None


def get_s3_client():
    """the client is made on the first use, so the app starts without aws keys"""
    global _client
    if _client is None:
        import boto3
        from botocore.config import Config

        _client = boto3.client(
            "s3",
            region_name=settings.S3_REGION,
            config=Config(signature_version="s3v4"),
        )
    return _client


def guess_content_type(filename: str) -> str:
    content_type, _ = mimetypes.guess_type(filename)
    return content_type or "application/octet-stream"


def build_temp_key(song_id: str, filename: str, kind: str) -> str:
    extension = os.path.splitext(filename)[1].lower()
    return f"{TEMP_PREFIX}/{song_id}/{kind}{extension}"


def build_final_key(temp_key: str) -> str:
    return f"{FINAL_PREFIX}/{temp_key.split('/', 1)[1]}"


def is_temp_key(key: str, song_id: str) -> bool:
    return key.startswith(f"{TEMP_PREFIX}/{song_id}/")

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


def create_upload_url(key: str, content_type: str) -> dict:
    """the link the client puts the file on"""
    url = get_s3_client().generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.S3_BUCKET,
            "Key": key,
            "ContentType": content_type,
        },
        ExpiresIn=settings.S3_UPLOAD_URL_EXPIRY,
    )

    return {
        "key": key,
        "url": url,
        "headers": {"Content-Type": content_type},
    }


def object_exists(key: str) -> bool:
    from botocore.exceptions import ClientError

    try:
        get_s3_client().head_object(Bucket=settings.S3_BUCKET, Key=key)
        return True
    except ClientError:
        return False


def copy_to_final_place(temp_key: str) -> str:
    """moves an uploaded file to the place the song files live"""
    final_key = build_final_key(temp_key)
    client = get_s3_client()

    client.copy_object(
        Bucket=settings.S3_BUCKET,
        Key=final_key,
        CopySource={"Bucket": settings.S3_BUCKET, "Key": temp_key},
        ContentType=guess_content_type(temp_key),
    )
    client.delete_object(Bucket=settings.S3_BUCKET, Key=temp_key)

    return final_key


def media_url(key: str) -> str:
    base = settings.MEDIA_BASE_URL or (
        f"https://{settings.S3_BUCKET}.s3.{settings.S3_REGION}.amazonaws.com"
    )
    return f"{base.rstrip('/')}/{key}"

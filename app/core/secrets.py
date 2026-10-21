from functools import lru_cache

import boto3

from app.core.config import settings


@lru_cache(maxsize=1)
def session_secret() -> str:
    """the secret that signs the session tokens

    it is in the environment when the app runs on a computer and in the
    parameter store when it runs on lambda
    """
    if settings.SESSION_SECRET:
        secret = settings.SESSION_SECRET
    elif settings.SESSION_SECRET_PARAMETER:
        client = boto3.client("ssm", region_name=settings.AWS_REGION)
        secret = client.get_parameter(
            Name=settings.SESSION_SECRET_PARAMETER,
            WithDecryption=True,
        )["Parameter"]["Value"]
    else:
        raise RuntimeError("the session secret is not set")

    if len(secret) < 32:
        raise RuntimeError("the session secret is too short")

    return secret

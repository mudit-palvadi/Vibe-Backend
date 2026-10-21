"""moves the users from the old postgres database to dynamodb

run it once with the database url of the old supabase project:
    python scripts/migrate_users_to_dynamodb.py
"""

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
from app.repositories.dynamodb_repositories import DynamoDbUserRepository  # noqa: E402


def get_connection():
    # psycopg2 does not know the sqlalchemy driver suffix
    url = settings.DATABASE_URL.replace("postgresql+psycopg2://", "postgresql://")
    return psycopg2.connect(url)


def get_users(connection) -> list[dict]:
    with connection.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute("select id, name, email, google_sub from users order by created_at")
        return cursor.fetchall()


def get_table():
    resource = boto3.resource("dynamodb", region_name=settings.AWS_REGION)
    return resource.Table(settings.DYNAMODB_TABLE_NAME)


def main() -> None:
    connection = get_connection()

    try:
        users = get_users(connection)
    finally:
        connection.close()

    users_repository = DynamoDbUserRepository(get_table())

    for user in users:
        users_repository.create(
            user_id=str(user["id"]),
            name=user["name"],
            email=user["email"],
            google_sub=user["google_sub"],
        )
        print(f"moved the user {user['email']}")

    print(f"moved {len(users)} users to dynamodb")


if __name__ == "__main__":
    main()

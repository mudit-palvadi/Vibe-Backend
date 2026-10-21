"""adds the google_sub column to the users table and fills it from the supabase auth data

run it once with the database url of the old supabase project:
    python scripts/migrate_google_sub.py
"""

import os
import sys

import psycopg2
from psycopg2.extras import RealDictCursor

# the script only needs the database url, so the other settings are not required
os.environ.setdefault("GOOGLE_CLIENT_ID", "not-needed-for-this-script")
os.environ.setdefault("SESSION_SECRET", "not-needed-for-this-script-but-long-enough")

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from app.core.config import settings  # noqa: E402


def get_connection():
    # psycopg2 does not know the sqlalchemy driver suffix
    url = settings.DATABASE_URL.replace("postgresql+psycopg2://", "postgresql://")
    return psycopg2.connect(url)


def add_google_sub_column(connection) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select column_name
            from information_schema.columns
            where table_name = 'users' and column_name = 'google_sub'
            """
        )

        if cursor.fetchone():
            print("the google_sub column is already there")
            return

        cursor.execute("alter table users add column google_sub varchar(255)")
        cursor.execute(
            "create unique index if not exists ix_users_google_sub on users (google_sub)"
        )

    connection.commit()
    print("added the google_sub column and its index")


def get_google_accounts(connection) -> list[dict]:
    with connection.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(
            """
            select u.email as email, i.provider_id as google_sub
            from auth.identities i
            join auth.users u on u.id = i.user_id
            where i.provider = 'google'
            """
        )
        return cursor.fetchall()


def fill_google_sub(connection) -> None:
    try:
        accounts = get_google_accounts(connection)
    except psycopg2.Error as e:
        connection.rollback()
        print(f"could not read the supabase accounts: {e}")
        return

    updated = 0

    with connection.cursor() as cursor:
        for account in accounts:
            cursor.execute(
                "update users set google_sub = %s where email = %s and google_sub is null",
                (account["google_sub"], account["email"]),
            )
            updated += cursor.rowcount

    connection.commit()
    print(f"filled google_sub for {updated} users")


def main() -> None:
    connection = get_connection()

    try:
        add_google_sub_column(connection)
        fill_google_sub(connection)
    finally:
        connection.close()


if __name__ == "__main__":
    main()

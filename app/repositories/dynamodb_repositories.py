"""the dynamodb version of the repositories

everything lives in one table, the key of an item says what the item is:

    USER#<user id>                    PROFILE              the user
    USER#<user id>                    FAV#<song id>        a favourite of the user
    USERGOOGLE#<google sub>           USER                 where the user with that google id is
    USEREMAIL#<email>                 USER                 where the user with that email is
    SONG#<song id>                    META                 the song
    SONGNAME#<name>#<song id>         <name>#<song id>     the song in the order of its name
    SONGARTIST#<artist>#<song id>     <name>#<song id>     the song in the order of its artist
    SONGTAG#<tag>#<song id>           <name>#<song id>     one item for every tag of the song
    PLAYLIST#<playlist id>            META                 the playlist
    PLAYLIST#<playlist id>            SONG#<time>#<song>   a song of the playlist
    USERPLAYLIST#<user id>#<list id>  <time>#<list id>    the playlist in the list of the user

the search runs on the folder of the index items, the name of the song is in
the sort key so the songs come back in the alphabetical order
"""

import uuid
from datetime import UTC, datetime

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from app.repositories.errors import (
    DuplicateSongError,
    PlaylistNotFoundError,
    SongNotFoundError,
    UserNotFoundError,
)
from app.repositories.protocols import (
    FavouriteRepository,
    PlaylistRepository,
    SongRepository,
    UserRepository,
)
from app.repositories.records import (
    FavouriteRecord,
    FavouriteWithSong,
    PlaylistRecord,
    SongRecord,
    UserRecord,
)
from app.repositories.tags import join_tags, parse_tags

PROFILE = "PROFILE"
POINTER = "USER"
TRANSACTION_LIMIT = 100


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _to_datetime(value) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


def _without_empty(item: dict) -> dict:
    """dynamodb does not take the keys that have no value"""
    return {key: value for key, value in item.items() if value is not None}


def _song_item(song: SongRecord) -> dict:
    return {
        "id": song.id,
        "song_name": song.song_name,
        "artist": song.artist,
        "song_url": song.song_url,
        "thumbnail_url": song.thumbnail_url,
        "tags": song.tags,
    }


def _to_song(item: dict) -> SongRecord:
    return SongRecord(
        id=item["id"],
        song_name=item["song_name"],
        artist=item["artist"],
        song_url=item["song_url"],
        thumbnail_url=item["thumbnail_url"],
        tags=item.get("tags", ""),
    )


class DynamoDbBase:
    """the little things every repository needs"""

    def __init__(self, table) -> None:
        self.table = table
        self.client = table.meta.client

    def _get(self, pk: str, sk: str) -> dict | None:
        return self.table.get_item(Key={"PK": pk, "SK": sk}).get("Item")

    def _query_prefix(self, prefix: str) -> list[dict]:
        """every item of the folder that starts with the prefix"""
        items = []
        request = {"KeyConditionExpression": Key("PK").begins_with(prefix)}
        while True:
            response = self.table.query(**request)
            items.extend(response.get("Items", []))
            last_key = response.get("LastEvaluatedKey")
            if not last_key:
                break
            request["ExclusiveStartKey"] = last_key
        return items

    def _write(self, items: list[dict]) -> None:
        """writes the items in one go, a transaction holds a hundred at most"""
        for start in range(0, len(items), TRANSACTION_LIMIT):
            self.client.transact_write_items(
                TransactItems=[
                    {"Put": {"TableName": self.table.name, "Item": item}}
                    for item in items[start : start + TRANSACTION_LIMIT]
                ]
            )

    def _delete(self, items: list[dict]) -> None:
        for start in range(0, len(items), TRANSACTION_LIMIT):
            self.client.transact_write_items(
                TransactItems=[
                    {
                        "Delete": {
                            "TableName": self.table.name,
                            "Key": {"PK": item["PK"], "SK": item["SK"]},
                        }
                    }
                    for item in items[start : start + TRANSACTION_LIMIT]
                ]
            )


class DynamoDbUserRepository(DynamoDbBase, UserRepository):
    def get_by_id(self, user_id: str) -> UserRecord | None:
        item = self._get(f"USER#{user_id}", PROFILE)
        if not item:
            return None
        return UserRecord(
            id=item["id"],
            name=item["name"],
            email=item["email"],
            google_sub=item.get("google_sub"),
            created_at=_to_datetime(item.get("created_at")),
            updated_at=_to_datetime(item.get("updated_at")),
        )

    def get_by_email(self, email: str) -> UserRecord | None:
        return self._by_pointer(f"USEREMAIL#{email.lower()}")

    def get_by_google_sub(self, google_sub: str) -> UserRecord | None:
        return self._by_pointer(f"USERGOOGLE#{google_sub}")

    def _by_pointer(self, pk: str) -> UserRecord | None:
        item = self._get(pk, POINTER)
        if not item:
            return None
        return self.get_by_id(item["user_id"])

    def create(self, *, name: str, email: str, google_sub: str | None = None) -> UserRecord:
        user_id = str(uuid.uuid4())
        now = _now()

        items = [
            _without_empty(
                {
                    "PK": f"USER#{user_id}",
                    "SK": PROFILE,
                    "entity": "user",
                    "id": user_id,
                    "name": name,
                    "email": email,
                    "google_sub": google_sub,
                    "created_at": now,
                    "updated_at": now,
                }
            ),
            {
                "PK": f"USEREMAIL#{email.lower()}",
                "SK": POINTER,
                "entity": "user_email",
                "user_id": user_id,
                "email": email,
            },
        ]

        if google_sub:
            items.append(
                {
                    "PK": f"USERGOOGLE#{google_sub}",
                    "SK": POINTER,
                    "entity": "user_google",
                    "user_id": user_id,
                    "google_sub": google_sub,
                }
            )

        self._write(items)

        return UserRecord(
            id=user_id,
            name=name,
            email=email,
            google_sub=google_sub,
            created_at=_to_datetime(now),
            updated_at=_to_datetime(now),
        )

    def set_google_sub(self, user_id: str, google_sub: str) -> UserRecord:
        user = self.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(user_id)

        self.client.transact_write_items(
            TransactItems=[
                {
                    "Update": {
                        "TableName": self.table.name,
                        "Key": {"PK": f"USER#{user_id}", "SK": PROFILE},
                        "UpdateExpression": "SET google_sub = :google_sub, updated_at = :updated_at",
                        "ExpressionAttributeValues": {
                            ":google_sub": google_sub,
                            ":updated_at": _now(),
                        },
                    }
                },
                {
                    "Put": {
                        "TableName": self.table.name,
                        "Item": {
                            "PK": f"USERGOOGLE#{google_sub}",
                            "SK": POINTER,
                            "entity": "user_google",
                            "user_id": user_id,
                            "google_sub": google_sub,
                        },
                    }
                },
            ]
        )

        return self.get_by_id(user_id)

    def set_name(self, user_id: str, name: str) -> UserRecord:
        user = self.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(user_id)

        self.table.update_item(
            Key={"PK": f"USER#{user_id}", "SK": PROFILE},
            UpdateExpression="SET #name = :name, updated_at = :updated_at",
            ExpressionAttributeNames={"#name": "name"},
            ExpressionAttributeValues={":name": name, ":updated_at": _now()},
        )

        return self.get_by_id(user_id)


class DynamoDbSongRepository(DynamoDbBase, SongRepository):
    def create(
        self,
        *,
        song_name: str,
        artist: str,
        song_url: str,
        thumbnail_url: str,
        tags: str,
        song_id: str | None = None,
    ) -> SongRecord:
        song_id = song_id or str(uuid.uuid4())
        tag_list = parse_tags(tags)
        song = SongRecord(
            id=song_id,
            song_name=song_name,
            artist=artist,
            song_url=song_url,
            thumbnail_url=thumbnail_url,
            tags=join_tags(tag_list),
        )
        details = _song_item(song)
        name_key = f"{song_name.lower()}#{song_id}"

        items = [
            {"PK": f"SONG#{song_id}", "SK": "META", "entity": "song", **details},
            {
                "PK": f"SONGNAME#{name_key}",
                "SK": name_key,
                "entity": "song_name",
                **details,
            },
            {
                "PK": f"SONGARTIST#{artist.lower()}#{song_id}",
                "SK": name_key,
                "entity": "song_artist",
                **details,
            },
        ]

        for tag in tag_list:
            items.append(
                {
                    "PK": f"SONGTAG#{tag.lower()}#{song_id}",
                    "SK": name_key,
                    "entity": "song_tag",
                    "tag": tag,
                    **details,
                }
            )

        self._write(items)

        return song

    def get(self, song_id: str) -> SongRecord | None:
        item = self._get(f"SONG#{song_id}", "META")
        if not item:
            return None
        return _to_song(item)

    def list_all(self) -> list[SongRecord]:
        return [_to_song(item) for item in self._query_prefix("SONGNAME#")]

    def search(self, query: str) -> list[SongRecord]:
        """the songs that start with the query, in the name, the artist, or a tag"""
        lowered = query.lower()
        found: dict[str, SongRecord] = {}

        for prefix in (
            f"SONGNAME#{lowered}",
            f"SONGARTIST#{lowered}",
            f"SONGTAG#{lowered}",
        ):
            for item in self._query_prefix(prefix):
                found.setdefault(item["id"], _to_song(item))

        return list(found.values())


class DynamoDbPlaylistRepository(DynamoDbBase, PlaylistRepository):
    def create(
        self,
        *,
        user_id: str,
        name: str,
        description: str | None = None,
        thumbnail_url: str | None = None,
    ) -> PlaylistRecord:
        playlist_id = str(uuid.uuid4())
        now = _now()

        details = _without_empty(
            {
                "id": playlist_id,
                "user_id": user_id,
                "name": name,
                "description": description,
                "thumbnail_url": thumbnail_url,
                "created_at": now,
            }
        )

        self._write(
            [
                {"PK": f"PLAYLIST#{playlist_id}", "SK": "META", "entity": "playlist", **details},
                {
                    "PK": f"USERPLAYLIST#{user_id}#{playlist_id}",
                    "SK": f"{now}#{playlist_id}",
                    "entity": "user_playlist",
                    **details,
                },
            ]
        )

        return PlaylistRecord(
            id=playlist_id,
            user_id=user_id,
            name=name,
            description=description,
            thumbnail_url=thumbnail_url,
            created_at=_to_datetime(now),
        )

    def get(self, playlist_id: str) -> PlaylistRecord | None:
        item = self._get(f"PLAYLIST#{playlist_id}", "META")
        if not item:
            return None
        return _to_playlist(item)

    def list_for_user(self, user_id: str) -> list[PlaylistRecord]:
        items = self._query_prefix(f"USERPLAYLIST#{user_id}#")
        return [_to_playlist(item) for item in items]

    def list_songs(self, playlist_id: str) -> list[SongRecord]:
        items = self.table.query(
            KeyConditionExpression=Key("PK").eq(f"PLAYLIST#{playlist_id}")
            & Key("SK").begins_with("SONG#")
        ).get("Items", [])

        items.sort(key=lambda item: item.get("added_at", ""))

        return [_to_song(item) for item in items]

    def add_song(self, *, playlist_id: str, song_id: str) -> None:
        playlist = self.get(playlist_id)
        if playlist is None:
            raise PlaylistNotFoundError(playlist_id)

        song = self._get(f"SONG#{song_id}", "META")
        if not song:
            raise SongNotFoundError(song_id)

        try:
            self.table.put_item(
                Item={
                    "PK": f"PLAYLIST#{playlist_id}",
                    "SK": f"SONG#{song_id}",
                    "entity": "playlist_song",
                    "added_at": _now(),
                    **_song_item(_to_song(song)),
                },
                ConditionExpression="attribute_not_exists(PK)",
            )
        except ClientError as error:
            if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise DuplicateSongError(song_id) from error
            raise

    def remove_song(self, *, playlist_id: str, song_id: str) -> bool:
        key = {"PK": f"PLAYLIST#{playlist_id}", "SK": f"SONG#{song_id}"}
        if not self.table.get_item(Key=key).get("Item"):
            return False

        self.table.delete_item(Key=key)
        return True

    def delete(self, playlist_id: str) -> None:
        playlist = self.get(playlist_id)
        if playlist is None:
            return

        songs = self.table.query(
            KeyConditionExpression=Key("PK").eq(f"PLAYLIST#{playlist_id}")
            & Key("SK").begins_with("SONG#")
        ).get("Items", [])

        items = [{"PK": f"PLAYLIST#{playlist_id}", "SK": "META"}]
        items.extend({"PK": f"PLAYLIST#{playlist_id}", "SK": item["SK"]} for item in songs)

        for item in self._query_prefix(f"USERPLAYLIST#{playlist.user_id}#"):
            if item.get("id") == playlist_id:
                items.append({"PK": item["PK"], "SK": item["SK"]})

        self._delete(items)


def _to_playlist(item: dict) -> PlaylistRecord:
    return PlaylistRecord(
        id=item["id"],
        user_id=item["user_id"],
        name=item["name"],
        description=item.get("description"),
        thumbnail_url=item.get("thumbnail_url"),
        created_at=_to_datetime(item.get("created_at")),
    )


class DynamoDbFavouriteRepository(DynamoDbBase, FavouriteRepository):
    def toggle(self, *, song_id: str, user_id: str) -> bool:
        key = {"PK": f"USER#{user_id}", "SK": f"FAV#{song_id}"}
        existing = self.table.get_item(Key=key).get("Item")

        if existing:
            self.table.delete_item(Key=key)
            return False

        song = self._get(f"SONG#{song_id}", "META")
        if not song:
            raise SongNotFoundError(song_id)

        self.table.put_item(
            Item={
                **key,
                "entity": "favourite",
                "id": str(uuid.uuid4()),
                "song_id": song_id,
                "user_id": user_id,
                "created_at": _now(),
                **_song_item(_to_song(song)),
            }
        )
        return True

    def get(self, *, song_id: str, user_id: str) -> FavouriteRecord | None:
        item = self._get(f"USER#{user_id}", f"FAV#{song_id}")
        if not item:
            return None
        return FavouriteRecord(id=item["id"], song_id=item["song_id"], user_id=item["user_id"])

    def list_for_user(self, user_id: str) -> list[FavouriteWithSong]:
        items = self.table.query(KeyConditionExpression=Key("PK").eq(f"USER#{user_id}")).get(
            "Items", []
        )

        favourites = []
        for item in items:
            if not item["SK"].startswith("FAV#"):
                continue
            favourites.append(
                FavouriteWithSong(
                    id=item["id"],
                    song_id=item["song_id"],
                    user_id=item["user_id"],
                    song=_to_song(item),
                )
            )

        return favourites

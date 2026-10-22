# The architecture of Vibe Backend

The details that do not fit in the [readme](../README.md): the two headers that matter through CloudFront, the shape of the DynamoDB table, the upload flow and the full file tree.

---

## How a request travels

```text
  Flutter app
      │
      │  x-vibe-auth: <session token>
      │  x-amz-content-sha256: <hash of the body>   (only when there is a body)
      ▼
  ┌────────────────┐
  │   CloudFront   │  distribution d3hb9a4bci0gq5.cloudfront.net
  └───────┬────────┘
          │  /songs/*  ──────────────► S3 bucket (the audio files and the covers)
          │  /*       ──────────────► Origin Access Control + SigV4
          ▼
  ┌────────────────┐
  │ Lambda (Mangum)│  python 3.13, fastapi behind app.lambda_handler.handler
  └───────┬────────┘
          ▼
  ┌────────────────┐
  │  DynamoDB      │  one table, provisioned capacity
  └────────────────┘
```

The song files never go through the Lambda. The client uploads them straight to the bucket with the links the backend gives it, and it reads them back through CloudFront.

---

## Two headers that matter through CloudFront

| Header | What it holds |
| :--- | :--- |
| `x-vibe-auth` | The session token of the user. |
| `x-amz-content-sha256` | The sha256 hash of the body, hex encoded. Only needed when the request has a body. |

CloudFront signs the request it forwards to the Lambda and replaces the `Authorization` header of the caller with that signature, so the session token needs its own header. The second one is there because the Lambda checks the hash of the body it receives. A request with a body and without that header comes back with a `403` and the message that the signature does not match.

The backend also reads the `Authorization: Bearer` header, so a call straight to the function url still works.

---

## The database

The app talks to the database through the repository interfaces in `app/repositories/`, so no route knows where the data lives. There are two implementations:

- `sqlmodel_repositories.py` for the old PostgreSQL database
- `dynamodb_repositories.py` for DynamoDB

The `DB_BACKEND` setting picks the one that is used. When it says `dynamodb` the PostgreSQL connection is never opened.

Everything sits in one DynamoDB table. The partition key and the sort key say what the item is:

```text
USER#<user id>                    PROFILE              the user
USER#<user id>                    FAV#<song id>        a favourite of the user
USEREMAIL#<email in lower case>   USER                 where the user with that email is
USERGOOGLE#<google sub>           USER                 where the user with that google id is
SONG#<song id>                    META                 the song
IDX_NAME                           <name>#<song id>     every song, in the order of its name
IDX_ARTIST                         <artist>#<song id>   every song, in the order of its artist
IDX_TAG                            <tag>#<name>#<id>    one item for every tag of the song
PLAYLIST#<playlist id>            META                 the playlist
PLAYLIST#<playlist id>            SONG#<song id>       a song of the playlist
IDX_USER_PLAYLIST#<user id>       <time>#<list id>     the playlists of the user
```

The prefix of a search goes in the sort key, so the songs come back already sorted and no index has to be paid for. The table is on provisioned capacity because the free tier of DynamoDB only pays for that.

The table and the rest of the infrastructure are made by the CDK stack in `infra/cdk`:

```bash
cd infra/cdk
cdk deploy VibeStack
```

---

## The song files

The audio files and the covers live in an S3 bucket. The client never sends them to the backend:

1. The client asks `POST /song/upload-init` with the title, the artist, the tags, and the file names. The backend answers with a song id and two upload links.
2. The client puts the files on those links with a plain `PUT` and the `Content-Type` header that was signed into the link. The links stop working after `S3_UPLOAD_URL_EXPIRY` seconds.
3. The client asks `POST /song/upload-complete` with the song id, the details of the song, and the two keys it used. The backend moves the files from `tmp/` to `songs/` and saves the song.

The files land in `tmp/` first. The bucket has a rule that removes everything in `tmp/` after a day, so an upload that was never finished does not stay there forever. The rule is made by this script:

```bash
python scripts/setup_s3_bucket.py
```

---

## The project structure

```text
server/
├── app/
│   ├── auth/
│   │   ├── google.py                # checks the google id token and swaps the refresh token
│   │   ├── jwks.py                  # checks a jwt against the public keys of a provider
│   │   └── session.py               # signs and checks the session tokens
│   ├── core/
│   │   ├── config.py                # the settings
│   │   └── secrets.py               # reads the session secret from the parameter store
│   ├── db/
│   │   └── database.py              # the engine and the session of the old database
│   ├── middleware/
│   │   └── auth_middleware.py       # finds the user of the session token
│   ├── models/                      # the sqlmodel models of the old database
│   │   ├── favourite.py
│   │   ├── playlist.py
│   │   ├── song.py
│   │   └── user.py
│   ├── repositories/
│   │   ├── dependencies.py          # gives the routes the repository they should use
│   │   ├── dynamodb_repositories.py # the dynamodb version
│   │   ├── errors.py                # the errors the repositories raise
│   │   ├── protocols.py             # the interface every repository follows
│   │   ├── records.py               # the plain records the repositories return
│   │   ├── sqlmodel_repositories.py # the postgres version
│   │   └── tags.py                  # reads and writes the tags of a song
│   ├── routes/
│   │   ├── auth_routes.py
│   │   ├── playlist_routes.py
│   │   └── song_routes.py
│   ├── schemas/                     # the request and response models
│   │   ├── favourite.py
│   │   ├── playlist.py
│   │   ├── song.py
│   │   └── user.py
│   ├── storage/
│   │   └── s3.py                    # the bucket client, the upload links, the file urls
│   ├── lambda_handler.py            # the handler that runs the app in the lambda
│   └── main.py                      # the app and the lifespan
├── docs/
│   ├── ARCHITECTURE.md              # this file
│   ├── DEPLOYMENT.md                # how the infrastructure goes up
│   └── MIGRATION.md                 # how the data moves from the old database
├── infra/
│   ├── cdk/                         # the aws infrastructure
│   └── lambda/requirements.txt      # the packages of the lambda
├── scripts/
│   ├── build_lambda_zip.py          # builds the zip of the lambda
│   ├── copy_media_to_s3.py          # copies the song files from cloudinary to the bucket
│   ├── migrate_content_to_dynamodb.py # moves the songs, the playlists, the favourites
│   ├── migrate_users_to_dynamodb.py # moves the users
│   └── setup_s3_bucket.py           # makes the bucket and the rule for unused uploads
├── tests/                           # the pytest suite
├── .github/workflows/ci.yml         # the lint and the tests on every push
├── .env.example
├── pyproject.toml                   # the ruff and the pytest settings
├── requirements.txt
└── requirements-dev.txt
```

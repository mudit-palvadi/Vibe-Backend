# Vibe Backend

[![CI](https://github.com/mudit-palvadi/Vibe-Backend/actions/workflows/ci.yml/badge.svg)](https://github.com/mudit-palvadi/Vibe-Backend/actions/workflows/ci.yml)

The backend of the **Vibe** music app. It is a FastAPI service that handles the sign in, the song uploads, the favourites, the playlists, and the search. It runs on AWS as a Lambda function behind CloudFront, the song files live in an S3 bucket, and the data lives in one DynamoDB table.

The users sign in with their Google account. There is no password, no user table of our own for the accounts, and no third party auth service in between. The backend checks the Google id token with the Google public keys and signs a session token of its own that the app sends with every request.

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

## Tech stack

| Piece | What it is used for |
| --- | --- |
| **FastAPI** | The web framework, the routes and the request models. |
| **Mangum** | Runs the FastAPI app inside the Lambda, the function is a normal event function. |
| **SQLModel** | The old PostgreSQL models. They are still used by the tests and by the migration scripts. |
| **DynamoDB** | The database the app uses now. Everything sits in one table, the key of an item says what the item is. |
| **Repositories** | The routes only talk to the repository interfaces, so the database can be swapped without touching a route. |
| **PyJWT & PyJWKClient** | Fetches the Google public keys, checks the Google id token, and signs the session tokens. |
| **Amazon S3** | Holds the audio files and the song covers. The client uploads to the bucket itself. |
| **AWS CDK** | The whole infrastructure, written in python: the table, the bucket, the function, the function url, the distribution. |
| **Pydantic Settings** | Reads the configuration from the environment and from the `.env` file. |

---

## Features

- **Google sign in.** The client sends the Google id token, the backend checks it against the Google public keys and signs a session token that lasts 30 days.
- **Session refresh.** The client keeps the Google refresh token, so the session can be renewed without sending the user through the Google screen again.
- **Direct uploads.** The song files go from the client to the bucket, the lambda never carries the payload.
- **Shared catalog.** Every song is visible to everyone, a user that uploads a song adds it for the whole app.
- **Search on the title, the artist, and the tags.** The search looks at the start of the word, the songs come back in the alphabetical order.
- **Favourites and playlists per user.** The data of the old accounts stays where it was, the first Google sign in finds the old account by the email.

---

## Endpoints

The session token goes in the **`x-vibe-auth`** header. CloudFront signs the request it sends to the Lambda and replaces the `Authorization` header of the caller with that signature, so the token needs its own header.

### Auth

| Method | Endpoint | Token | What it does |
| :--- | :--- | :---: | :--- |
| `POST` | `/auth/login` | no | Takes the Google id token in the body, answers with a session token that lasts 30 days. |
| `POST` | `/auth/refresh` | yes | Takes the Google refresh token in the body and answers with a new session token. |
| `GET` | `/auth` | yes | Answers with the user and their favourite songs. |

### Songs

| Method | Endpoint | Token | What it does |
| :--- | :--- | :---: | :--- |
| `POST` | `/song/upload-init` | yes | Answers with a song id and two upload links, one for the audio and one for the cover. |
| `POST` | `/song/upload-complete` | yes | Moves the uploaded files to their place and saves the song. |
| `GET` | `/song/list` | yes | Lists every song of the catalog. |
| `GET` | `/song/search?q=` | yes | Searches by the start of the title, the artist, or a tag. |
| `POST` | `/song/favourite` | yes | Adds the song to the favourites of the user or takes it away again. |
| `GET` | `/song/list-favourites` | yes | Answers with the favourite songs of the user. |

### Playlists

| Method | Endpoint | Token | What it does |
| :--- | :--- | :---: | :--- |
| `POST` | `/playlist/create` | yes | Makes a new playlist. |
| `GET` | `/playlist/list` | yes | Lists the playlists of the user. |
| `GET` | `/playlist/{playlist_id}` | yes | Answers with a playlist and its songs. |
| `POST` | `/playlist/add-song` | yes | Puts a song in a playlist. |
| `DELETE` | `/playlist/remove-song` | yes | Takes a song out of a playlist. |
| `DELETE` | `/playlist/{playlist_id}` | yes | Deletes a playlist. |

---

## Two headers that matter through CloudFront

| Header | What it holds |
| :--- | :--- |
| `x-vibe-auth` | The session token of the user. |
| `x-amz-content-sha256` | The sha256 hash of the body, hex encoded. Only needed when the request has a body. |

The second one is there because CloudFront signs the request it forwards to the Lambda, and the Lambda checks the hash of the body it receives. A request with a body and without that header comes back with a `403` and the message that the signature does not match.

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

## The sign in

1. The app opens the system browser with the Google authorization url and a PKCE code challenge.
2. Google sends the user back to `http://localhost:8000` with an authorization code.
3. The app trades that code for an id token and a refresh token.
4. The app sends the id token to `POST /auth/login`. The backend checks it with the Google public keys, finds or makes the user, and answers with a session token that lasts 30 days.
5. The app sends that session token in the `x-vibe-auth` header of every request.
6. When the session token is about to run out, the app sends the Google refresh token to `POST /auth/refresh` together with the session token. The backend checks the refresh token with Google and answers with a new session token.
7. When Google says the refresh token is not valid any more, the backend answers with a `401` and the app does the Google sign in again.

The Google refresh token never reaches the database and never reaches the server, it stays on the client.

### Setting up the Google client

1. Open the [Google Cloud console](https://console.cloud.google.com/) and pick the project the app should use.
2. Enable the **Google Identity Services** API under **APIs & Services**.
3. Set up the **OAuth consent screen** first. Pick the **Testing** type and add the accounts of the people that use the app as **test users**, a testing app only lets those accounts in.
4. Create the credentials: **Create credentials** → **OAuth client ID**.
5. Pick the application type **Web application**. The Flutter package opens the system browser and comes back to `http://localhost:8000`, so that address has to be the **Authorized redirect URI**. The secret of a web client is not a real secret, the app is a public client on the desktop.
6. Put the client id and the client secret in the `.env` of the server as `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`, and in the `.env` of the Flutter app with the same names. The server also reads both from the parameter store (`/vibe/google-client-id` and `/vibe/google-client-secret`), so the Lambda always has the right ones after a deploy.

---

## Configuration

Copy `.env.example` to `.env` in the root of the server folder:

```ini
DB_BACKEND=dynamodb
DYNAMODB_TABLE_NAME=vibe
AWS_REGION=ap-south-1

GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

SESSION_SECRET=
SESSION_SECRET_PARAMETER=/vibe/session-secret
SESSION_TTL_DAYS=30
SESSION_ISSUER=vibe-backend

S3_BUCKET=
S3_REGION=ap-south-1
MEDIA_BASE_URL=
S3_UPLOAD_URL_EXPIRY=900
```

| Setting | Where it comes from |
| :--- | :--- |
| `DB_BACKEND`, `DYNAMODB_TABLE_NAME`, `AWS_REGION` | the values of the deployed stack, `dynamodb` and `vibe` in `ap-south-1`. |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | Google Cloud console, **Credentials** → the OAuth client. The stack also keeps them in the parameter store. |
| `SESSION_SECRET` | signs the session tokens. When it changes every user has to sign in again. When it is empty the secret is read from the parameter store `/vibe/session-secret`, that is how the Lambda gets it. |
| `S3_BUCKET` | the name of the bucket the CDK stack made. |
| `MEDIA_BASE_URL` | the address of the CloudFront distribution, the song urls in the database are built from it. |
| `DATABASE_URL` | the old PostgreSQL database. Only the migration scripts need it. |

---

## Running it locally

**Python 3.13** and the dependencies:

```bash
python -m venv venv
```

```powershell
.\venv\Scripts\Activate.ps1     # windows
```

```bash
source venv/bin/activate        # linux and mac
```

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The service runs on `http://127.0.0.1:8000` and the api docs are on `http://127.0.0.1:8000/docs`.

### The tests

The tests run on a temporary sqlite database, they never touch the real one:

```bash
pip install -r requirements-dev.txt
pytest
```

The suite has a contract layer. The same tests run against the SQLModel repositories and against DynamoDB, the DynamoDB run needs a real table and is off by default:

```bash
RUN_DYNAMODB_TESTS=1 pytest tests/test_dynamodb_contracts.py
```

---

## Deploying

The infrastructure is described in [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md). The short version:

```bash
python scripts/build_lambda_zip.py      # the lambda needs the linux wheels of the packages
cd infra/cdk
cdk deploy VibeStack
```

The Lambda is a zip of the app, the package is built with the linux wheels so it can be under the size limit of 50 MB.

---

## The live api

| | |
| :--- | :--- |
| **Base url** | [https://d3hb9a4bci0gq5.cloudfront.net](https://d3hb9a4bci0gq5.cloudfront.net) |
| **Swagger UI** | [https://d3hb9a4bci0gq5.cloudfront.net/docs](https://d3hb9a4bci0gq5.cloudfront.net/docs) |
| **ReDoc** | [https://d3hb9a4bci0gq5.cloudfront.net/redoc](https://d3hb9a4bci0gq5.cloudfront.net/redoc) |

---

## The old accounts

The users of the old database keep their account, their id, their favourites, and their playlists. The first sign in with Google looks for the Google id, and when it is not there yet it looks for the email, so the old favourites and playlists stay where they were.

The move of the data is written down in [docs/MIGRATION.md](docs/MIGRATION.md).

---

## The free plan

The aws account is on the free plan, so the CloudFront flat rate plan cannot be used for it. The distribution is on the pay as you go pricing, which gives 1 TB of traffic and 10 million requests for free every month. The web acl of CloudFront is not used, it costs about 5 dollars a month and would eat the credits of the account. The `EdgeStack` in `infra/cdk/edge_stack.py` holds that web acl and comes back when the account is on the paid plan.

---

## Project structure

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

---

## The client

The Flutter app that talks to this backend lives in [mudit-palvadi/Vibe](https://github.com/mudit-palvadi/Vibe). Its readme has the details of the app itself.

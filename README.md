# Vibe Backend

[![CI](https://github.com/mudit-palvadi/Vibe-Backend/actions/workflows/ci.yml/badge.svg)](https://github.com/mudit-palvadi/Vibe-Backend/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.13-blue?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136.1-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Lambda](https://img.shields.io/badge/AWS_Lambda-FF9900?logo=aws&logoColor=white)](https://aws.amazon.com/lambda/)
[![DynamoDB](https://img.shields.io/badge/Amazon_DynamoDB-FF9900?logo=aws&logoColor=white)](https://aws.amazon.com/dynamodb/)
[![S3](https://img.shields.io/badge/Amazon_S3-FF9900?logo=aws&logoColor=white)](https://aws.amazon.com/s3/)
[![CloudFront](https://img.shields.io/badge/Amazon_CloudFront-FF9900?logo=aws&logoColor=white)](https://aws.amazon.com/cloudfront/)
[![Google OAuth](https://img.shields.io/badge/Google_OAuth-4285F4?logo=google&logoColor=white)](https://developers.google.com/identity/protocols/oauth2)
[![Ruff](https://img.shields.io/badge/ruff-0.17.1-261230)](https://docs.astral.sh/ruff/)
[![pytest](https://img.shields.io/badge/pytest-9.1.1-0A9EDC?logo=pytest&logoColor=white)](https://pytest.org/)

The backend of the **Vibe** music app. A FastAPI service that does the sign in, the song uploads, the favourites, the playlists and the search.

It runs on AWS: a Lambda behind CloudFront, the song files in an S3 bucket, the data in one DynamoDB table. The users sign in with their Google account, there is no password and no auth service in between — the backend checks the Google id token with the Google public keys and signs a session token of its own that the app sends with every request.

The Flutter app that talks to it lives in [mudit-palvadi/Vibe](https://github.com/mudit-palvadi/Vibe).

---

## How a request travels

```text
  Flutter app  ──►  CloudFront  ──►  Lambda (FastAPI)  ──►  DynamoDB
                          │
                          └──  /songs/*  ───────────────►  S3 (the audio and the covers)
```

The song files never go through the Lambda. The app uploads them straight to the bucket with the links the backend gives it, and reads them back through CloudFront.

---

## What it does

- **Google sign in.** The app sends the Google id token, the backend checks it and signs a session token that lasts 30 days.
- **Session refresh.** The app keeps the Google refresh token, so the session can be renewed without sending the user through the Google screen again.
- **Direct uploads.** The files go from the app to the bucket, the Lambda never carries the payload.
- **Shared catalog.** Every song is visible to everyone, whoever uploads a song adds it for the whole app.
- **Search** on the start of the title, the artist or a tag, the songs come back in the alphabetical order.
- **Favourites and playlists per user.** The old accounts keep their id, their favourites and their playlists.

---

## The endpoints

The session token goes in the **`x-vibe-auth`** header. A request that has a body also needs **`x-amz-content-sha256`**, the sha256 of the body in hex. Both are explained in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

| Method | Endpoint | What it does |
| :--- | :--- | :--- |
| `POST` | `/auth/login` | Takes the Google id token in the body, answers with a session token that lasts 30 days. |
| `POST` | `/auth/refresh` | Takes the Google refresh token in the body, answers with a new session token. |
| `GET` | `/auth` | Answers with the user and their favourite songs. |
| `POST` | `/song/upload-init` | Answers with a song id and two upload links, one for the audio and one for the cover. |
| `POST` | `/song/upload-complete` | Moves the uploaded files to their place and saves the song. |
| `GET` | `/song/list` | Lists every song of the catalog. |
| `GET` | `/song/search?q=` | Searches by the start of the title, the artist or a tag. |
| `POST` | `/song/favourite` | Adds the song to the favourites of the user or takes it away again. |
| `GET` | `/song/list-favourites` | Answers with the favourite songs of the user. |
| `POST` | `/playlist/create` | Makes a new playlist. |
| `GET` | `/playlist/list` | Lists the playlists of the user. |
| `GET` | `/playlist/{playlist_id}` | Answers with a playlist and its songs. |
| `POST` | `/playlist/add-song` | Puts a song in a playlist. |
| `DELETE` | `/playlist/remove-song` | Takes a song out of a playlist. |
| `DELETE` | `/playlist/{playlist_id}` | Deletes a playlist. |

---

## The sign in

1. The app opens the system browser with the Google authorization url and a PKCE code challenge.
2. Google sends the user back to `http://localhost:8000` with an authorization code.
3. The app trades that code for an id token and a refresh token, and sends the id token to `POST /auth/login`.
4. The backend checks the id token, finds or makes the user, and answers with a session token.
5. The app sends that token in the `x-vibe-auth` header of every request, and renews it with `POST /auth/refresh` when it is about to run out.

The Google refresh token never reaches the server, it stays on the app.

### Setting up the Google client

1. Open the [Google Cloud console](https://console.cloud.google.com/), pick the project, and enable the **Google Identity Services** API.
2. Set up the **OAuth consent screen** first. Use the **Testing** type and add the accounts that use the app as **test users**, a testing app only lets those accounts in.
3. **Create credentials** → **OAuth client ID** → application type **Web application**. The app comes back to `http://localhost:8000`, so that address has to be the **Authorized redirect URI**.
4. Put the client id and the client secret in the `.env` of the server as `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`. The stack also keeps them in the parameter store, so the Lambda always has the right ones after a deploy.

---

## Running it locally

```bash
python -m venv venv
.\venv\Scripts\Activate.ps1     # windows
source venv/bin/activate        # linux and mac
pip install -r requirements.txt -r requirements-dev.txt
uvicorn app.main:app --reload
```

The service runs on `http://127.0.0.1:8000` and the api docs are on `http://127.0.0.1:8000/docs`.

The tests run on a temporary sqlite database, they never touch the real one:

```bash
pytest
```

The suite has a contract layer: the same tests run against the SQLModel repositories and against DynamoDB. The DynamoDB run needs a real table and is off by default:

```bash
RUN_DYNAMODB_TESTS=1 pytest tests/test_dynamodb_contracts.py
```

The settings come from the environment and from a `.env` file in the root. Copy `.env.example` to `.env` and fill it in, the table of every setting and where it comes from is in [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

---

## Deploying

The infrastructure is a CDK stack written in python, it makes the table, the bucket, the function, the function url and the distribution:

```bash
python scripts/build_lambda_zip.py      # the lambda needs the linux wheels of the packages
cd infra/cdk
cdk deploy VibeStack
```

The whole runbook, with the bootstrap of the account, the parameter store and the free plan, is in [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## The live api

| | |
| :--- | :--- |
| **Base url** | [https://d3hb9a4bci0gq5.cloudfront.net](https://d3hb9a4bci0gq5.cloudfront.net) |
| **Swagger UI** | [https://d3hb9a4bci0gq5.cloudfront.net/docs](https://d3hb9a4bci0gq5.cloudfront.net/docs) |
| **ReDoc** | [https://d3hb9a4bci0gq5.cloudfront.net/redoc](https://d3hb9a4bci0gq5.cloudfront.net/redoc) |

---

## The data

The users of the old database keep their account, their id, their favourites and their playlists. The first sign in with Google looks for the Google id, and when it is not there yet it looks for the email, so the old favourites and playlists stay where they were.

The move of the data is written down in [docs/MIGRATION.md](docs/MIGRATION.md).

---

## The free plan

The aws account is on the free plan, so the distribution is on the pay as you go pricing, which gives 1 TB of traffic and 10 million requests for free every month. The web acl of CloudFront is not used, it costs about 5 dollars a month and would eat the credits of the account. It comes back when the account is on the paid plan.

---

## The layout

```text
server/
├── app/            the backend: the routes, the repositories, the auth, the storage
├── tests/          the pytest suite
├── docs/           the deployment, the migration and the architecture
├── infra/cdk/      the aws infrastructure
├── scripts/        the bucket, the lambda zip and the data migration
└── pyproject.toml  the ruff and the pytest settings
```

The routes never talk to the database directly, they go through the repository interfaces, so the database can be swapped without touching a route. The key scheme of the table, the two headers and the full file tree are in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

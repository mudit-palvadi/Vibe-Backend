# Vibe Backend

This is the backend for the Vibe music app I am creating. It is built using FastAPI and SQLModel to handle the core server-side operations, including user authentication, song uploads, managing favorites, custom user playlists, and search filtering.

The server uploads and hosts media assets (audio files and image thumbnails) directly on Cloudinary. The users sign in with their Google account, the backend checks the Google id token with the Google public keys and hands out a session token that the app uses for every request.

---

## Tech Stack

Here is what I am using to build the backend:

- **FastAPI**: The web framework for handling API routes and requests.
- **SQLModel**: The database toolkit that combines SQLAlchemy and Pydantic so I can write pythonic database models.
- **PostgreSQL**: The relational database for storing app data.
- **PyJWT & PyJWKClient**: To fetch the Google public signature keys and verify the id token of the user, and to sign the session tokens.
- **Cloudinary**: For storing and serving audio files and song covers.
- **Pydantic Settings**: For loading configuration settings from environment files.

---

## Core Features

- **Google sign in**: The client sends the Google id token, the backend checks it against the Google public keys and signs a session token that lasts 30 days.
- **Session refresh**: The client keeps the Google refresh token, so the session token can be renewed without sending the user through the Google screen again.
- **Database Unique Constraints**: Added unique constraints at the database level to prevent duplicate favorites and duplicate songs in the same playlist.
- **Optimized Queries**: Uses SQLAlchemy joinedload options to eagerly load database relations and prevent slow N+1 query execution.
- **Type-Safe Serialization**: Implements custom Pydantic response models to make sure the server returns consistent JSON payloads to the Flutter client.
- **Real-time search**: Offers case-insensitive search filtering across song titles, artists, and tag lists.

---

## File Structure

Here is how the project files are laid out:

```text
server/
├── app/
│   ├── auth/
│   │   ├── google.py               # Google id token check and refresh token exchange
│   │   ├── jwks.py                 # Verifies a jwt against the public keys of a provider
│   │   └── session.py              # Signs and checks the session tokens
│   ├── core/
│   │   └── config.py             # Environment configuration settings
│   ├── db/
│   │   └── database.py           # Database engine setup and session factory
│   ├── middleware/
│   │   └── auth_middleware.py    # Authentication middleware guards
│   ├── models/
│   │   ├── favourite.py          # User favorite songs model
│   │   ├── playlist.py           # Playlist and playlist_songs junction tables
│   │   ├── song.py               # Song metadata model
│   │   └── user.py               # User profile model
│   ├── routes/
│   │   ├── auth_routes.py        # Authentication routes
│   │   ├── playlist_routes.py    # Playlist management routes
│   │   └── song_routes.py        # Song listing, upload, and search routes
│   ├── schemas/
│   │   ├── favourite.py          # Favorite request schemas
│   │   ├── playlist.py           # Playlist request/response schemas
│   │   ├── song.py               # Song response schemas
│   │   └── user.py               # User and auth response schemas
│   └── main.py                   # App entrypoint and database lifespan setup
├── scripts/
│   └── migrate_google_sub.py     # Adds the google_sub column and fills it from supabase
├── tests/                        # Pytest suite, it runs on a temporary sqlite database
├── .env                          # Configuration environment variables
├── .env.example                  # The same variables with empty values
├── .gitignore                    # Ignored files for git
├── requirements.txt              # Project dependencies list
└── README.md                     # This file
```

---

## API Endpoints

### Auth Endpoints

| Method | Endpoint         | Requires Token? | Description                                                              |
| :----- | :--------------- | :-------------: | :----------------------------------------------------------------------- |
| `POST` | `/auth/login`    |       No        | Takes the Google id token and returns a session token.                    |
| `POST` | `/auth/refresh`  |       Yes       | Renews the session token with the Google refresh token of the client.     |
| `GET`  | `/auth/`         |       Yes       | Returns the logged-in user profile with their favorite songs.             |

### Song Endpoints

| Method | Endpoint                | Requires Token? | Description                                                          |
| :----- | :---------------------- | :-------------: | :------------------------------------------------------------------- |
| `POST` | `/song/upload`          |       Yes       | Uploads a song audio and thumbnail to Cloudinary and saves metadata. |
| `GET`  | `/song/list`            |       Yes       | Lists all available songs.                                           |
| `GET`  | `/song/search`          |       Yes       | Searches the library case-insensitively by title, artist, or tags.   |
| `POST` | `/song/favourite`       |       Yes       | Toggles a song as a user favorite.                                   |
| `GET`  | `/song/list-favourites` |       Yes       | Returns all the user's favorite songs.                               |

### Playlist Endpoints

| Method   | Endpoint                  | Requires Token? | Description                                |
| :------- | :------------------------ | :-------------: | :----------------------------------------- |
| `POST`   | `/playlist/create`        |       Yes       | Creates a new playlist.                    |
| `GET`    | `/playlist/list`          |       Yes       | Lists all playlists owned by the user.     |
| `GET`    | `/playlist/{playlist_id}` |       Yes       | Returns a playlist with its list of songs. |
| `POST`   | `/playlist/add-song`      |       Yes       | Adds a song to a playlist.                 |
| `DELETE` | `/playlist/remove-song`   |       Yes       | Removes a song from a playlist.            |
| `DELETE` | `/playlist/{playlist_id}` |       Yes       | Deletes a playlist.                        |

---

## Getting Started

### Prerequisites

Make sure you have python (3.10+) and a PostgreSQL instance running locally or hosted online.

### Configuration

Copy the `.env.example` file to `.env` in the root of the server folder and fill in the values:

```ini
DATABASE_URL=postgresql://<username>:<password>@<host>:<port>/<database_name>
SUPABASE_URL=https://<your-project-id>.supabase.co
CLOUDINARY_CLOUD_NAME=<your-cloudinary-cloud-name>
CLOUDINARY_API_KEY=<your-cloudinary-api-key>
CLOUDINARY_API_SECRET=<your-cloudinary-api-secret>
GOOGLE_CLIENT_ID=<the client id of the google desktop app>
GOOGLE_CLIENT_SECRET=<the client secret of the google desktop app>
SESSION_SECRET=<a long random string of at least 32 characters>
SESSION_TTL_DAYS=30
```

The `SESSION_SECRET` signs the session tokens. When it changes, every user has to sign in again.

### Google OAuth Setup

The users sign in with their Google account, there is no password and no user database of our own for the accounts.

1. Open the [Google Cloud console](https://console.cloud.google.com/) and pick the project the app should use.
2. Go to **APIs & Services** and enable the **Google Identity Services** API for that project.
3. Go to **Credentials** and press **Create credentials** and then **OAuth client ID**.
4. Pick the application type **Desktop app** and give it a name. Desktop apps are public clients, so the secret is not kept a secret.
5. Google registers the loopback addresses (`http://127.0.0.1` and `http://localhost`) for a desktop app. The app opens the system browser on a free port and waits for the answer there, so no redirect url has to be added by hand.
6. Put the client id and the client secret in the `.env` file as `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`.

The sign in on the client side works like this:

1. The app opens the system browser with the Google authorization url and a PKCE code challenge.
2. Google sends the user back to the loopback address with an authorization code.
3. The app trades that code for an id token and a refresh token. The id token lasts about an hour, the refresh token stays valid until the user signs out of the app.
4. The app sends the id token to `POST /auth/login`. The backend checks the id token with the Google public keys, finds or makes the user, and answers with a session token that lasts 30 days.
5. The app sends that session token in the `Authorization: Bearer <session token>` header of every request.
6. When the session token is about to run out, the app sends the Google refresh token to `POST /auth/refresh` together with the session token. The backend checks the refresh token with Google and answers with a new session token.
7. If Google says the refresh token is not valid anymore, the backend answers with a 401 and the app does the Google sign in again.

The Google refresh token never reaches the database, it stays on the client.

### The old accounts

The users that signed in with Supabase keep their account. The `users` table got a `google_sub` column with the Google id of the account, and the script below fills it:

```bash
python scripts/migrate_google_sub.py
```

The script adds the column when it is not there yet, then it reads the Google accounts from the old Supabase project and puts the Google id next to the email of the user. The first login with Google finds the account by that Google id, and if it is not there yet it looks for the email, so the old favorites and playlists stay where they are.

### Installation

1. Open your terminal in the server folder and set up a virtual environment:

   ```bash
   python -m venv venv
   ```

2. Activate the virtual environment:
   - Windows (PowerShell):
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```
   - Linux / macOS:
     ```bash
     source venv/bin/activate
     ```

3. Install the dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Start up the backend:
   ```bash
   uvicorn app.main:app --reload
   ```

The backend server runs locally at `http://127.0.0.1:8000`.

### Tests

The tests run on a temporary sqlite database, so they do not touch the real one:

```bash
pip install -r requirements-dev.txt
pytest
```

### Live Hosted API & Docs

The backend is publicly hosted and running on Oracle Cloud. You can connect to the API or browse the documentation directly using these links:
* **Live Swagger UI**: [http://152.67.191.54:8000/docs](http://152.67.191.54:8000/docs)
* **Live ReDoc view**: [http://152.67.191.54:8000/redoc](http://152.67.191.54:8000/redoc)

---

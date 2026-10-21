import os
import tempfile
from uuid import UUID

# the settings are read at import time, so they have to be set before the app is imported
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-google-client-id")
os.environ.setdefault("SESSION_SECRET", "test-session-secret-that-is-long-enough-123")

# the tests always run on the local database, the .env file of the machine
# points at dynamodb
os.environ["DB_BACKEND"] = "sqlmodel"

import pytest
from fastapi.testclient import TestClient
from jwks_server import JwksTestServer, build_key_pair
from sqlmodel import Session, SQLModel, create_engine

from app.db.database import get_session
from app.main import app
from app.models.song import Song
from app.models.user import User

test_db_path = os.path.join(tempfile.mkdtemp(prefix="vibe-tests-"), "test.db")
test_engine = create_engine(
    f"sqlite:///{test_db_path}",
    connect_args={"check_same_thread": False},
)

TEST_SUB = "11111111-1111-4111-8111-111111111111"
TEST_EMAIL = "test@example.com"


@pytest.fixture(scope="session")
def jwks_server():
    """a jwks server on localhost so the tests can use real signed tokens"""
    server = JwksTestServer(build_key_pair()).start()
    yield server
    server.stop()


@pytest.fixture()
def db():
    SQLModel.metadata.drop_all(test_engine)
    SQLModel.metadata.create_all(test_engine)
    yield test_engine
    SQLModel.metadata.drop_all(test_engine)


@pytest.fixture()
def session(db):
    with Session(db) as test_session:
        yield test_session


@pytest.fixture()
def token_payload():
    return {
        "sub": TEST_SUB,
        "google_sub": "google-sub-1",
        "email": TEST_EMAIL,
        "name": "Test User",
    }


@pytest.fixture(autouse=True)
def mock_verify_session_token(token_payload, monkeypatch):
    """The session tokens are not signed in the tests."""
    monkeypatch.setattr(
        "app.middleware.auth_middleware.verify_session_token",
        lambda token: dict(token_payload),
    )
    return token_payload


@pytest.fixture()
def auth_headers():
    return {"Authorization": "Bearer test-token"}


@pytest.fixture()
def current_user(session, token_payload):
    user = User(
        id=UUID(token_payload["sub"]),
        name="Test User",
        email=token_payload["email"],
        google_sub=token_payload["google_sub"],
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture()
def song(session):
    test_song = Song(
        id="song-1",
        song_name="Test Song",
        artist="Test Artist",
        song_url="https://example.com/song.mp3",
        thumbnail_url="https://example.com/thumb.jpg",
        tags="pop,test",
    )
    session.add(test_song)
    session.commit()
    session.refresh(test_song)
    return test_song


@pytest.fixture()
def client(db):
    def override_get_session():
        with Session(db) as test_session:
            yield test_session

    app.dependency_overrides[get_session] = override_get_session
    # the app is used without the lifespan, so the app engine is never touched
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()

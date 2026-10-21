import os
import tempfile
from uuid import UUID

# the settings are read at import time, so they have to be set before the app is imported
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("CLOUDINARY_CLOUD_NAME", "test-cloud")
os.environ.setdefault("CLOUDINARY_API_KEY", "test-key")
os.environ.setdefault("CLOUDINARY_API_SECRET", "test-secret")

import pytest
from fastapi.testclient import TestClient
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
        "email": TEST_EMAIL,
        "user_metadata": {"full_name": "Test User"},
    }


@pytest.fixture(autouse=True)
def mock_verify_token(token_payload, monkeypatch):
    """The google/supabase tokens are not verified in the tests."""
    monkeypatch.setattr(
        "app.middleware.auth_middleware.verify_token", lambda token: dict(token_payload)
    )
    monkeypatch.setattr("app.routes.auth_routes.verify_token", lambda token: dict(token_payload))
    return token_payload


@pytest.fixture()
def auth_headers():
    return {"Authorization": "Bearer test-token"}


@pytest.fixture()
def current_user(session, token_payload):
    user = User(id=UUID(token_payload["sub"]), name="Test User", email=token_payload["email"])
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

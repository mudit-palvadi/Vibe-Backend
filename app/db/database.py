from sqlmodel import Session, create_engine

from app.core.config import settings

engine = create_engine(settings.DATABASE_URL, echo=True)


def get_session():
    """the postgres session is only opened when the app still uses it"""
    if settings.DB_BACKEND == "dynamodb":
        yield None
        return

    with Session(engine) as session:
        yield session

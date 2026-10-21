from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

from app.models.favourite import Favourite


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)

    name: str

    email: str = Field(unique=True, index=True)

    # the id of the google account, this is what we log in with now
    google_sub: str | None = Field(default=None, unique=True, index=True)

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    favourites: list["Favourite"] = Relationship(back_populates="user")

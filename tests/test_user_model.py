import pytest
from sqlalchemy.exc import IntegrityError

from app.models.user import User


def test_a_user_keeps_the_google_sub(session):
    user = User(name="Someone", email="someone@gmail.com", google_sub="google-sub-1")
    session.add(user)
    session.commit()
    session.refresh(user)

    assert user.google_sub == "google-sub-1"


def test_a_user_without_a_google_sub_is_allowed(session):
    user = User(name="Someone", email="someone@gmail.com")
    session.add(user)
    session.commit()
    session.refresh(user)

    assert user.google_sub is None


def test_two_users_cannot_share_the_same_google_sub(session):
    session.add(User(name="One", email="one@gmail.com", google_sub="google-sub-1"))
    session.commit()

    session.add(User(name="Two", email="two@gmail.com", google_sub="google-sub-1"))

    with pytest.raises(IntegrityError):
        session.commit()

    session.rollback()

from fastapi import HTTPException
from jwks_server import sign_google_token

from app.auth.session import verify_session_token
from app.core.config import settings


def test_the_login_refresh_and_me_flow(client, session, jwks_server, monkeypatch):
    # the real session tokens are used in this flow
    monkeypatch.setattr("app.middleware.auth_middleware.verify_session_token", verify_session_token)
    monkeypatch.setattr(settings, "GOOGLE_JWKS_URL", jwks_server.url)
    monkeypatch.setattr(
        "app.routes.auth_routes.exchange_refresh_token",
        lambda refresh_token: {"access_token": "a-new-google-access-token"},
    )

    # the client signs in with the google id token
    id_token = sign_google_token(jwks_server, sub="google-sub-1", email="someone@gmail.com")
    login = client.post("/auth/login", json={"id_token": id_token})

    assert login.status_code == 200
    session_token = login.json()["session_token"]

    # the client asks for its own data with the session token
    me = client.get("/auth/", headers={"Authorization": f"Bearer {session_token}"})

    assert me.status_code == 200
    assert me.json()["email"] == "someone@gmail.com"
    assert me.json()["id"] == login.json()["user"]["id"]

    # the client refreshes the session with the google refresh token
    refresh = client.post(
        "/auth/refresh",
        json={"refresh_token": "a-google-refresh-token"},
        headers={"Authorization": f"Bearer {session_token}"},
    )

    assert refresh.status_code == 200
    new_session_token = refresh.json()["session_token"]
    assert new_session_token

    # the new session token works as well
    me = client.get("/auth/", headers={"Authorization": f"Bearer {new_session_token}"})

    assert me.status_code == 200
    assert me.json()["email"] == "someone@gmail.com"


def test_the_flow_stops_when_the_google_session_is_over(client, jwks_server, monkeypatch):
    monkeypatch.setattr("app.middleware.auth_middleware.verify_session_token", verify_session_token)
    monkeypatch.setattr(settings, "GOOGLE_JWKS_URL", jwks_server.url)

    def broken_exchange(refresh_token):
        raise HTTPException(status_code=401, detail="Google session is not valid anymore")

    monkeypatch.setattr("app.routes.auth_routes.exchange_refresh_token", broken_exchange)

    id_token = sign_google_token(jwks_server, sub="google-sub-1", email="someone@gmail.com")
    login = client.post("/auth/login", json={"id_token": id_token})
    session_token = login.json()["session_token"]

    refresh = client.post(
        "/auth/refresh",
        json={"refresh_token": "a-dead-refresh-token"},
        headers={"Authorization": f"Bearer {session_token}"},
    )

    assert refresh.status_code == 401

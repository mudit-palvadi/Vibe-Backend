"""a tiny jwks server so the tests can sign real tokens and verify them"""

import json
import threading
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from app.core.config import settings

TEST_KID = "vibe-test-key"


def build_key_pair() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def build_jwk(private_key: rsa.RSAPrivateKey, kid: str = TEST_KID) -> dict:
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key()))
    jwk.update({"kid": kid, "alg": "RS256", "use": "sig"})
    return jwk


class _JwksHandler(BaseHTTPRequestHandler):
    jwks: dict = {}

    def do_GET(self):  # noqa: N802
        body = json.dumps(self.jwks).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class JwksTestServer:
    """serves a jwks on localhost and signs the tokens with the matching key"""

    def __init__(self, private_key: rsa.RSAPrivateKey, kid: str = TEST_KID):
        self.private_key = private_key
        self.kid = kid
        self.jwk = build_jwk(private_key, kid)
        handler = type("Handler", (_JwksHandler,), {"jwks": {"keys": [self.jwk]}})
        self.server = HTTPServer(("127.0.0.1", 0), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def url(self) -> str:
        host, port = self.server.server_address[:2]
        return f"http://{host}:{port}/.well-known/jwks.json"

    def sign(self, payload: dict, kid: str | None = None) -> str:
        return jwt.encode(
            payload,
            self.private_key,
            algorithm="RS256",
            headers={"kid": kid or self.kid},
        )

    def start(self) -> "JwksTestServer":
        self.thread.start()
        return self

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()


def sign_google_token(server: JwksTestServer, drop: tuple[str, ...] = (), **overrides) -> str:
    """signs a google id token like the one the client sends after a google login"""
    payload = {
        "sub": "google-sub-1",
        "email": "someone@gmail.com",
        "name": "Someone",
        "iss": "https://accounts.google.com",
        "aud": settings.GOOGLE_CLIENT_ID,
        "exp": int((datetime.now(UTC) + timedelta(hours=1)).timestamp()),
    }

    payload.update(overrides)

    for claim in drop:
        payload.pop(claim, None)

    return server.sign(payload)

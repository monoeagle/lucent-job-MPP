from datetime import datetime, timedelta, timezone

import jwt

from app.domain.auth import User, Role

STUB_USERS = [
    User(
        username="test-requester",
        display_name="Test Requester",
        email="requester@test.local",
        roles=[Role.REQUESTER],
    ),
    User(
        username="test-approver",
        display_name="Test Approver",
        email="approver@test.local",
        roles=[Role.APPROVER],
    ),
    User(
        username="test-admin",
        display_name="Test Admin",
        email="admin@test.local",
        roles=[Role.ADMIN],
    ),
    User(
        username="test-multi",
        display_name="Test Multi Role",
        email="multi@test.local",
        roles=[Role.REQUESTER, Role.APPROVER, Role.ADMIN],
    ),
]

_STUB_USER_MAP = {u.username: u for u in STUB_USERS}


class AuthService:
    class InvalidCredentialsError(Exception):
        pass

    class TokenExpiredError(Exception):
        pass

    class InvalidTokenError(Exception):
        pass

    def __init__(self, auth_mode: str, jwt_secret: str, token_ttl_seconds: int):
        self.auth_mode = auth_mode
        self.jwt_secret = jwt_secret
        self.token_ttl_seconds = token_ttl_seconds

    def login(self, username: str, password: str | None) -> dict:
        if self.auth_mode == "stub":
            return self._stub_login(username)
        raise NotImplementedError("LDAP auth not implemented yet")

    def _stub_login(self, username: str) -> dict:
        user = _STUB_USER_MAP.get(username)
        if user is None:
            raise self.InvalidCredentialsError("invalid credentials")

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=self.token_ttl_seconds)

        claims = user.to_jwt_claims()
        claims["iat"] = now
        claims["exp"] = expires_at

        token = jwt.encode(claims, self.jwt_secret, algorithm="HS256")

        return {
            "token": token,
            "user": {
                "username": user.username,
                "display_name": user.display_name,
                "email": user.email,
                "roles": list(user.roles),
            },
            "expires_at": expires_at.isoformat().replace("+00:00", "Z"),
        }

    def verify_token(self, token: str) -> User:
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            raise self.TokenExpiredError("token expired")
        except jwt.InvalidTokenError:
            raise self.InvalidTokenError("invalid token")

        return User(
            username=payload["sub"],
            display_name=payload["display_name"],
            email=payload["email"],
            roles=payload["roles"],
        )

    def get_stub_users(self) -> list[dict]:
        return [
            {
                "username": u.username,
                "display_name": u.display_name,
                "email": u.email,
                "roles": list(u.roles),
                "hint": "Use for self-approval tests"
                if u.username == "test-multi"
                else "Login without password or use 'stub-password'",
            }
            for u in STUB_USERS
        ]
